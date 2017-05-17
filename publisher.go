package main

import (
	"fmt"
	"time"
	"net/http"
	"io/ioutil"
	"log"
	"github.com/jlaffaye/ftp"
	"bytes"
	"sync"
	"io"
)

var lock = &sync.Mutex{}
var wg = &sync.WaitGroup{}


func processFiles(files <- chan string) {
	defer wg.Done()
	conn, err := connectToFtp()
	if err != nil {
		log.Fatal("Unable to connect to FTP server exiting - aborting")
	}
	defer conn.Logout()
	defer conn.Quit()
	for file := range files {
		buf, err := getFileFromFTP(file, conn)
		if err == nil {
			status, err := postFileToRas(file, &buf)
			if status == 200 && err == nil {
				deleteFileOnFTP(conn, file)
			}
		}
	}

}
func deleteFileOnFTP(conn *ftp.ServerConn, file string) {
	err := conn.Delete(file)
	if err != nil {
		log.Printf("Unable to delete file %s", file)
	}
}


func getFileFromFTP(file string, conn *ftp.ServerConn) ([]byte, error)  {
	content, err := conn.Retr(file)
	defer content.Close()
	if err != nil {
		log.Print("Unable to retrieve file")
		return nil, err
	}
	buf, err := ioutil.ReadAll(content)
	if err != nil {
		log.Print("Unable to stream file")
		return nil, err

	}
	return buf, nil
}


func postFileToRas(file string, buf *[]byte) (int, error) {
	resp, err := http.Post("http://localhost:8080/upload/bres/1/"+ file,
		"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
		bytes.NewReader(*buf))
	if resp != nil {
		defer resp.Body.Close()
	}
	if err != nil {
		log.Printf("Unable to send file %s to RAS", file)
		return 0, err
	}
	return resp.StatusCode, nil

}

func connectToFtp() (*ftp.ServerConn, error) {
	var err error
	lock.Lock()
	defer lock.Unlock()
	conn, err := ftp.Connect("localhost:2021")
	if err != nil {
		log.Print(err)
		return nil, err
	}
	conn.Login("ons", "ons")
	return conn, err
}

func main() {

	go webServer()
	for {
		log.Print("Start of for loop")
		startTime := time.Now()
		conn, err := connectToFtp()
		if err != nil {
			log.Print("FTP unavailable")
			wait()
			continue
		}
		files, err := conn.List("/")
		if err != nil {
			log.Print("Unable to list files on FTP server")
			wait()
			continue
		}

		fileNames := make(chan string)

		//fan out a 10 go rountines
		for i := 0; i < 10; i++ {
			wg.Add(1)
			go processFiles(fileNames)
		}

		for _, file := range files {
			//fmt.Println("File name " + file.Name)
			fileNames <- file.Name
		}

		close(fileNames)
		wg.Wait()
		elapsed := time.Since(startTime)
		fmt.Printf("Total time %s", elapsed)
		fmt.Println()
		conn.Logout()
		conn.Quit()
		wait()
	}

}

func wait() {
	time.Sleep(time.Minute * 1)
}

func webServer() {
	http.HandleFunc("/healthcheck", healthCheck)
	http.ListenAndServe(":8090", http.DefaultServeMux)
}


func healthCheck(w http.ResponseWriter, r *http.Request) {
	ftpRunning := checkFtp()
	rasRunning := checkRas()
	status := "FAILED"
	if checkRas() && checkFtp() {
		status = "OK"
	}
	json := fmt.Sprintf("{\"status\":\"%s\",\"ftp\":%t,\"ras\":%t}", status, ftpRunning, rasRunning)
	io.WriteString(w, json)
}

func checkFtp() bool {
	conn, err := connectToFtp()
	if conn != nil {
		defer conn.Quit()
		defer conn.Logout()
	}
	if err != nil {
		log.Print("FTP healthcheck failed")
	} else {
		log.Print("FTP healthcheck sucessful")
	}
	return err == nil
}

func checkRas() bool {
	resp, err := http.Head("http://localhost:8080/healthcheck")
	if err != nil || resp.StatusCode != http.StatusOK {
		log.Print("RAS healthcheck failed")
	} else{
		log.Print("RAS healthcheck successful")
	}
	return resp.StatusCode == http.StatusOK
}