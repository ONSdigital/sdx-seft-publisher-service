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

func handleError(err error) {
	if err != nil {
		log.Fatal(err)
	}
}

func poll_ftp() {
	fmt.Println("Poll ftp")
	conn, err := ftp.Connect("localhost:2021")
	handleError(err)

	conn.Login("ons", "ons")
	files, err := conn.List("/")
	handleError(err)

	for _, file := range  files {
		fmt.Println("File name " + file.Name)
		go readAndPublish(file)
	}
	conn.Logout()
	conn.Quit()
}

func readAndPublish(file *ftp.Entry) {
	conn, err := ftp.Connect("localhost:2021")
	handleError(err)
	conn.Login("ons", "ons")
	content, err := conn.Retr(file.Name)
	handleError(err)
	buf, err := ioutil.ReadAll(content)
	handleError(err)
	content.Close()
	publish(file.Name, buf, conn)
	conn.Logout()
	conn.Quit()
}

func publish(fileName string, buf []byte, conn *ftp.ServerConn) {
	fmt.Println("Publishing file")
	resp, err := http.Post("http://localhost:8080/upload/bres/1/" + fileName,
		"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
		bytes.NewReader(buf))
	handleError(err)
	result, err := ioutil.ReadAll(resp.Body)
	handleError(err)
	resp.Body.Close()
	fmt.Printf("%s", result)
	if resp.StatusCode == 200 {
		delete(fileName, conn)
	}
}

func delete(fileName string, conn *ftp.ServerConn) {
	err := conn.Delete(fileName)
	handleError(err)
}

func main() {
	fmt.Println("Starting publisher")
	for {
		poll_ftp()
		time.Sleep(time.Minute * 15)
	}
}