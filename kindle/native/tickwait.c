/* Event wait: input from powerd wakes the clock immediately after an RTC resume. */
#include <sys/stat.h>
#include <fcntl.h>
#include <poll.h>
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
int main(int argc,char **argv){
 if(argc!=3)return 2;int seconds=atoi(argv[2]);if(seconds<1||seconds>3600)return 2;
 int fd=open(argv[1],O_RDWR|O_NONBLOCK);if(fd<0)return 1;
 struct pollfd p={fd,POLLIN,0};int n;
 do{n=poll(&p,1,seconds*1000);}while(n<0&&errno==EINTR);
 if(n<0){close(fd);return 1;}
 if(n>0){char buf[512];ssize_t len=read(fd,buf,sizeof(buf));if(len>0)fwrite(buf,1,(size_t)len,stdout);}
 close(fd);return 0;
}
