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
)

var lock = &sync.Mutex{}
var wg = &sync.WaitGroup{}


func handleError(err error) {
	if err != nil {
		log.Print(err)
		panic(err)
	}
}


func read(files <- chan string) {
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
	//fmt.Println("Starting publisher")

	startTime := time.Now()
	//fmt.Println("Poll ftp")
	conn := connectToFtp()
	files, err := conn.List("/")
	handleError(err)
	defer conn.Logout()
	defer conn.Quit()
	fileNames := make(chan string)

	//fan out a 20 go rountines
	for i := 0; i < 10; i++ {
		read(fileNames)
	}

	for _, file := range files {
		//fmt.Println("File name " + file.Name)
		fileNames <- file.Name
	}

	close(fileNames)
	wg.Wait()
	elasped := time.Since(startTime)
	fmt.Printf("Total time %s", elasped)
	fmt.Println()

}