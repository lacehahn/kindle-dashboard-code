/* JSON report -> existing raster commands. jsmn: MIT, see vendor/jsmn.h. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "vendor/jsmn.h"
int main(int argc,char **argv){
 if(argc!=2&&argc!=3)return 2;FILE *f=fopen(argv[1],"rb");if(!f)return 2;
 fseek(f,0,SEEK_END);long n=ftell(f);rewind(f);if(n<1||n>500000){fclose(f);return 2;}
 char *data=calloc((size_t)n+1,1);jsmntok_t *tokens=calloc(20000,sizeof(*tokens));
 if(!data||!tokens||fread(data,1,(size_t)n,f)!=(size_t)n)return 2;fclose(f);
 jsmn_parser parser;jsmn_init(&parser);int count=jsmn_parse(&parser,data,(size_t)n,tokens,20000);
 if(count<1||tokens[0].type!=JSMN_OBJECT)return 2;
 int array=-1,version=0,assets=-1,bundle=-1,portrait=-1,generated=-1,epoch=-1;
 for(int i=1;i<count;i++){
  if(tokens[i].type!=JSMN_STRING||tokens[i].parent!=0)continue;
  int len=tokens[i].end-tokens[i].start;
  if(len==17&&!strncmp(data+tokens[i].start,"portrait_commands",17)&&i+1<count&&tokens[i+1].type==JSMN_ARRAY)portrait=i+1;
  if(len==15&&!strncmp(data+tokens[i].start,"generated_epoch",15)&&i+1<count&&tokens[i+1].type==JSMN_PRIMITIVE)epoch=i+1;
  if(len==12&&!strncmp(data+tokens[i].start,"generated_at",12)&&i+1<count&&tokens[i+1].type==JSMN_STRING)generated=i+1;
  if(len==14&&!strncmp(data+tokens[i].start,"schema_version",14)&&i+1<count)version=atoi(data+tokens[i+1].start);
  if(len==6&&!strncmp(data+tokens[i].start,"assets",6)&&i+1<count&&tokens[i+1].type==JSMN_OBJECT)assets=i+1;
  if(len==12&&!strncmp(data+tokens[i].start,"asset_bundle",12)&&i+1<count&&tokens[i+1].type==JSMN_STRING)bundle=i+1;
  if(len==8&&!strncmp(data+tokens[i].start,"commands",8)&&i+1<count&&tokens[i+1].type==JSMN_ARRAY)array=i+1;
 }
 if(version!=1||array<0)return 2;
 if(argc==3&&!strcmp(argv[2],"--portrait")){if(portrait<0)return 2;array=portrait;}
 if(argc==3&&strcmp(argv[2],"--portrait")){
  if(!strcmp(argv[2],"--epoch")){
   if(epoch<0)return 2;int len=tokens[epoch].end-tokens[epoch].start;if(len<1||len>11)return 2;
   for(int k=tokens[epoch].start;k<tokens[epoch].end;k++)if(data[k]<'0'||data[k]>'9')return 2;
   printf("%.*s\n",len,data+tokens[epoch].start);return 0;
  }
  if(!strcmp(argv[2],"--stamp")){
   if(generated<0||tokens[generated].end-tokens[generated].start<16)return 2;
   int offsets[]={0,1,2,3,5,6,8,9,11,12,14,15};
   for(int k=0;k<12;k++){char c=data[tokens[generated].start+offsets[k]];if(c<'0'||c>'9')return 2;putchar(c);}putchar('\n');return 0;
  }
  if(!strcmp(argv[2],"--bundle")){
   if(bundle<0||tokens[bundle].end-tokens[bundle].start!=64)return 2;
   for(int k=tokens[bundle].start;k<tokens[bundle].end;k++)if(!strchr("0123456789abcdef",data[k]))return 2;
   printf("%.*s\n",64,data+tokens[bundle].start);return 0;
  }
  if(strcmp(argv[2],"--assets")||assets<0)return 2;
  for(int i=assets+1;i<count&&tokens[i].start<tokens[assets].end;i+=2){
   if(i+1>=count||tokens[i].parent!=assets||tokens[i+1].parent!=i||tokens[i].type!=JSMN_STRING||tokens[i+1].type!=JSMN_STRING)return 2;
   int len=tokens[i].end-tokens[i].start;if(len<5||len>64)return 2;
   for(int k=tokens[i].start;k<tokens[i].end;k++)if(!strchr("abcdefghijklmnopqrstuvwxyz0123456789_.-",data[k]))return 2;
   if(tokens[i+1].end-tokens[i+1].start!=64)return 2;
   for(int k=tokens[i+1].start;k<tokens[i+1].end;k++)if(!strchr("0123456789abcdef",data[k]))return 2;
   printf("%.*s|%.*s\n",len,data+tokens[i].start,64,data+tokens[i+1].start);
  }
  return 0;
 }
 int lines=0;
 for(int i=array+1;i<count&&tokens[i].start<tokens[array].end;i++){
  if(tokens[i].parent!=array||tokens[i].type!=JSMN_STRING)return 2;
  int len=tokens[i].end-tokens[i].start;if(len<3||len>2048)return 2;
  char line[2049];int out=0;
  for(int k=tokens[i].start;k<tokens[i].end;k++){
   char c=data[k];if(c=='\\'){if(++k>=tokens[i].end)return 2;c=data[k];if(c!='"'&&c!='\\'&&c!='/')return 2;}
   if((unsigned char)c<32)return 2;line[out++]=c;
  }
  line[out]=0;if(line[1]!='|'||!strchr("TIR",line[0]))return 2;
  if(line[0]=='I'&&!strstr(line,"|/mnt/us/dashboard/icons/")&&!strstr(line,"|/mnt/us/dashboard/bg_report.png"))return 2;
  if(strstr(line,".."))return 2;
  puts(line);lines++;
 }
 free(data);free(tokens);return lines?0:2;
}
