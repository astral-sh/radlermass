package main

import (
	"fmt"

	greeting "example.com/radlermass-test"
)

var version = "dev"
var commit = "unknown"

func main() {
	fmt.Println(greeting.Message)
	fmt.Println(version)
	fmt.Println(commit)
}
