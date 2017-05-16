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
	_ "net/http/pprof"
	"io"
)

var lock = &sync.Mutex{}
var wg = &sync.WaitGroup{}


func handleError(err error) {
	if err != nil {
		log.Print(err)
		panic(err)
	}
}


func processFiles(files <- chan string) {
	wg.Add(1)
	go func() {
		defer wg.Done()
		conn := connectToFtp()
		defer conn.Logout()
		defer conn.Quit()
		for file := range files {
			content, err := conn.Retr(file)
			handleError(err)
			buf, err := ioutil.ReadAll(content)
			handleError(err)
			content.Close()

			//fmt.Println("Publishing file")
			resp, err := http.Post("http://localhost:8080/upload/bres/1/"+ file,
				"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
				bytes.NewReader(buf))
			handleError(err)
			//_, err := ioutil.ReadAll(resp.Body)
			//handleError(err)
			//fmt.Printf("%s", result)

			resp.Body.Close()

			if resp.StatusCode == 200 {
				err := conn.Delete(file)
				handleError(err)
			}

		}

	}()
}


func connectToFtp() *ftp.ServerConn {
	lock.Lock()
	conn, err := ftp.Connect("localhost:2021")
	handleError(err)
	conn.Login("ons", "ons")
	lock.Unlock()
	return conn
}

func main() {

	go webServer()
	//fmt.Println("Starting publisher")
	time.Sleep(time.Second * 10)
	for {
		startTime := time.Now()
		//fmt.Println("Poll ftp")
		conn := connectToFtp()
		files, err := conn.List("/")
		handleError(err)
		defer conn.Logout()
		defer conn.Quit()
		fileNames := make(chan string)

		//fan out a 10 go rountines
		for i := 0; i < 10; i++ {
			processFiles(fileNames)
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
		time.Sleep(time.Minute)
	}

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
	conn := connectToFtp()
	_, err := conn.List("/")
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