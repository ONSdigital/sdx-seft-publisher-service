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

type File struct {
	buf []byte
	fileName string
	respCode int
}

func handleError(err error) {
	if err != nil {
		log.Fatal(err)
	}
}

func pollFtp() {

	//fmt.Println("Poll ftp")
	conn := connectToFtp()
	files, err := conn.List("/")
	handleError(err)
	defer conn.Quit()
	defer conn.Logout()

	out := make(chan *File)

	//fan out a 20 go rountines
	for i := 0; i < 20; i++ {
		readChannel := read(out)
		publishChannel := publish(readChannel)
		delete(publishChannel)
	}

	for _, file := range  files {
		//fmt.Println("File name " + file.Name)
		out <- &File{nil, file.Name, 0}
	}

	close(out)
}

func read(in <- chan *File) <- chan *File {
	out := make(chan *File)
	wg.Add(1)
	go func() {
		conn := connectToFtp()
		defer conn.Quit()
		defer conn.Logout()

		for file := range in {
			content, err := conn.Retr(file.fileName)
			handleError(err)
			buf, err := ioutil.ReadAll(content)
			file.buf = buf
			handleError(err)
			content.Close()
			out <- file
		}
		close(out)
		wg.Done()
	}()
	return out
}

func publish(in <- chan *File) <- chan *File {
	out := make(chan *File)
	wg.Add(1)
	go func () {
		for file := range in {

			//fmt.Println("Publishing file")
			resp, err := http.Post("http://localhost:8080/upload/bres/1/"+ file.fileName,
				"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
				bytes.NewReader(file.buf))
			handleError(err)
			//result, err := ioutil.ReadAll(resp.Body)
			//handleError(err)
			//fmt.Printf("%s", result)
			file.respCode = resp.StatusCode
			resp.Body.Close()
			out <- file
		}
		close(out)
		wg.Done()
	}()
	return out
}

func delete(in <- chan *File) {
	wg.Add(1)
	go func() {
		conn := connectToFtp()
		defer conn.Quit()
		defer conn.Logout()

		for file := range in {
			if file.respCode == 200 {
				err := conn.Delete(file.fileName)
				handleError(err)
			}
		}
		wg.Done()
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
	pollFtp()
	wg.Wait()
	elasped := time.Since(startTime)
	fmt.Printf("Total time %s", elasped)
	fmt.Println()

}