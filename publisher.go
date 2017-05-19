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
	"mime/multipart"
	"io"
	"strings"
)

var lock = &sync.Mutex{}
var wg = &sync.WaitGroup{}

func main() {

	go func() {
		http.HandleFunc("/healthcheck", healthCheck)
		http.ListenAndServe(":8090", http.DefaultServeMux)
	}()

	//ticker := time.NewTicker(time.Minute * 1)
	//for t := range ticker.C {
	//	log.Println("About to poll FTP ", t)
		startTime := time.Now()
		conn, err := connectToFtp()
		if err != nil {
			log.Print("FTP unavailable")
			//continue
		}
		files, err := conn.List("/")
		if err != nil {
			log.Print("Unable to list files on FTP server")
			//continue
		}
		conn.Quit()
		fileNames := make(chan string)

		//fan out a 10 go rountines
		for i := 0; i < 1; i++ {
			wg.Add(1)
			go processFiles(fileNames)
		}

		for _, file := range files {
			if strings.HasSuffix(file.Name, ".xlsx") {
				fileNames <- file.Name
			}
		}

		close(fileNames)
		wg.Wait()
		elapsed := time.Since(startTime)
		log.Printf("Total time %s", elapsed)
	//}

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
		log.Print(err)
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

	// Prepare a form that you will submit to that URL.
	var b bytes.Buffer
	w := multipart.NewWriter(&b)
	defer w.Close()

	fw, err := w.CreateFormFile("files[]", file)
	if err != nil {
		log.Print("Failed to create form file", err)
		return false
	}

	if _, err = io.Copy(fw, bytes.NewReader(*buf)); err != nil {
		log.Print("Failed to copy file", err)
		return false
	}

	resp, err := http.Post("http://ras-collection-instrument-demo.apps.mvp.onsclofo.uk/collection-instrument-api/1.0.2/upload/456/" + file,
		"Content-Type:"+ w.FormDataContentType(), &b)

	if err != nil {
		log.Printf("Unable to send file %s to RAS", file)
		return false
	}

	result, _ := ioutil.ReadAll(resp.Body)
	log.Printf("%s", result)

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
