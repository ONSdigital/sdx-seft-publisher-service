package main

import (
	"time"
	"net/http"
	"io/ioutil"
	"log"
	"github.com/jlaffaye/ftp"
	"bytes"
	"sync"
	"encoding/json"
)

var lock = &sync.Mutex{}
var wg = &sync.WaitGroup{}

func main() {

	go func() {
		http.HandleFunc("/healthcheck", healthCheck)
		http.ListenAndServe(":8090", http.DefaultServeMux)
	}()

	ticker := time.NewTicker(time.Minute * 1)
	for t := range ticker.C {
		log.Println("About to poll FTP ", t)
		startTime := time.Now()
		conn, err := connectToFtp()
		if err != nil {
			log.Print("FTP unavailable")
			continue
		}
		files, err := conn.List("/")
		if err != nil {
			log.Print("Unable to list files on FTP server")
			continue
		}
		conn.Quit()
		fileNames := make(chan string)

		//fan out a 10 go rountines
		for i := 0; i < 10; i++ {
			wg.Add(1)
			go processFiles(fileNames)
		}

		for _, file := range files {
			fileNames <- file.Name
		}

		close(fileNames)
		wg.Wait()
		elapsed := time.Since(startTime)
		log.Printf("Total time %s", elapsed)
	}

}

type HealthCheck struct {
	Status string
	Ftp string
	Ras string
}

func healthCheck(w http.ResponseWriter, _ *http.Request) {
	ok := "OK"
	failed := "FAILED"
	var status, ftpStatus, rasStatus = ok, ok, ok

	if !checkRas() {
		status, rasStatus = failed, failed
	}
	if !checkFtp() {
		status, ftpStatus = failed, failed
	}

	response, err := json.Marshal(&HealthCheck{status, ftpStatus, rasStatus})
	if err != nil {
		log.Print(err)
		w.WriteHeader(http.StatusInternalServerError)
		return
	}
	w.Write(response)
}

func processFiles(files <- chan string) {
	defer wg.Done()
	conn, err := connectToFtp()
	if err != nil {
		log.Fatal("Unable to connect to FTP server exiting - aborting")
	}
	defer conn.Quit()
	for file := range files {
		buf := getFileFromFTP(file, conn)
		if buf != nil {
			if postFileToRas(file, &buf) {
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


func getFileFromFTP(file string, conn *ftp.ServerConn) ([]byte)  {
	content, err := conn.Retr(file)
	defer content.Close()
	if err != nil {
		log.Print("Unable to retrieve file")
		return nil
	}
	buf, err := ioutil.ReadAll(content)
	if err != nil {
		log.Print("Unable to stream file")
		return nil

	}
	return buf
}


func postFileToRas(file string, buf *[]byte) ( bool) {
	resp, err := http.Post("http://localhost:8080/upload/bres/1/"+ file,
		"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
		bytes.NewReader(*buf))
	if err != nil {
		log.Printf("Unable to send file %s to RAS", file)
		return false
	}
	defer resp.Body.Close()
	if  resp.StatusCode != http.StatusOK {
		log.Printf("Failed to send file to RAS status code %s", resp.StatusCode)
		return false
	}
	return true

}

func connectToFtp() (*ftp.ServerConn, error) {
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


func checkFtp() bool {
	conn, err := connectToFtp()
	if err != nil {
		log.Print("FTP healthcheck failed")
	} else {
		log.Print("FTP healthcheck sucessful")
		defer conn.Logout()
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
