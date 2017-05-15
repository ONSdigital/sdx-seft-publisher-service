package main

import (
	"fmt"
	"time"
	"net/http"
	"io/ioutil"
	"log"
	"github.com/jlaffaye/ftp"
	"bytes"
)

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

func poll_ftp() {
	fmt.Println("Poll ftp")
	conn := connectToFtp()
	files, err := conn.List("/")
	handleError(err)
	defer conn.Logout()
	defer conn.Quit()

	for _, file := range  files {
		fmt.Println("File name " + file.Name)
		readChannel := read(file)
		publishChannel := publish(readChannel)
		delete(publishChannel)
	}
}

func read(file *ftp.Entry) <- chan File {
	out := make(chan File)
	go func() {
		conn := connectToFtp()
		defer conn.Logout()
		defer conn.Quit()

		content, err := conn.Retr(file.Name)
		defer content.Close()
		handleError(err)
		buf, err := ioutil.ReadAll(content)
		res := File{buf, file.Name, 0}
		handleError(err)
		out <- res
		close(out)
	}()
	return out
}

func publish(in <- chan File) <- chan File {
	out := make(chan File)
	go func () {
		for file := range in {

			fmt.Println("Publishing file")
			resp, err := http.Post("http://localhost:8080/upload/bres/1/"+ file.fileName,
				"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
				bytes.NewReader(file.buf))
			handleError(err)
			result, err := ioutil.ReadAll(resp.Body)
			handleError(err)
			resp.Body.Close()
			fmt.Printf("%s", result)
			file.respCode = resp.StatusCode
			out <- file
		}
		close(out)
	}()
	return out

}

func delete(in <- chan File) {
	go func() {
		conn := connectToFtp()
		defer conn.Logout()
		defer conn.Quit()
		for file := range in {
			if file.respCode == 200 {
				err := conn.Delete(file.fileName)
				handleError(err)
			}
		}
	}()
}
func connectToFtp() *ftp.ServerConn {
	conn, err := ftp.Connect("localhost:2021")
	handleError(err)
	conn.Login("ons", "ons")

	return conn
}

func main() {
	fmt.Println("Starting publisher")
	for {
		poll_ftp()
		time.Sleep(time.Minute * 15)
	}
}