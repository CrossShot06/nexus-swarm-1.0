FROM alpine:latest

RUN apk update && apk add g++

WORKDIR /sandbox