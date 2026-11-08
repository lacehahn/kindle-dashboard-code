/* Validate Open-Meteo JSON before replacing the persistent weather snapshot. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include "vendor/jsmn.h"
static char data[100001];static jsmntok_t t[6000];static int count;
static int member(int obj,const char *key){for(int i=obj+1;i<count&&t[i].start<t[obj].end;i++)if(t[i].parent==obj&&t[i].type==JSMN_STRING&&t[i].end-t[i].start==(int)strlen(key)&&!strncmp(data+t[i].start,key,strlen(key)))return i+1;return -1;}
static int element(int arr,int n){if(arr<0||t[arr].type!=JSMN_ARRAY)return -1;for(int i=arr+1;i<count&&t[i].start<t[arr].end;i++)if(t[i].parent==arr&&n--==0)return i;return -1;}
static int number(int i,double *out){if(i<0||t[i].type!=JSMN_PRIMITIVE)return 0;char *end;double v=strtod(data+t[i].start,&end);if(end!=data+t[i].end||!isfinite(v))return 0;*out=v;return 1;}
static int textdate(int i,char *out,int len){if(i<0||t[i].type!=JSMN_STRING||t[i].end-t[i].start!=len)return 0;memcpy(out,data+t[i].start,len);out[len]=0;for(int j=0;j<len;j++){char c=out[j];if(j==4||j==7){if(c!='-')return 0;}else if(j==10){if(c!='T')return 0;}else if(j==13){if(c!=':')return 0;}else if(c<'0'||c>'9')return 0;}return 1;}
int main(int argc,char **argv){
 if(argc!=2)return 2;FILE *f=fopen(argv[1],"rb");if(!f)return 2;size_t n=fread(data,1,sizeof(data)-1,f);int more=fgetc(f);fclose(f);if(!n||more!=EOF)return 2;
 jsmn_parser p;jsmn_init(&p);count=jsmn_parse(&p,data,n,t,6000);if(count<1||t[0].type!=JSMN_OBJECT)return 2;
 int cur=member(0,"current"),daily=member(0,"daily");if(cur<0||daily<0)return 2;
 char time[17],dates[4][11];double temp,hum,wind,code,hi[4],lo[4],codes[4];
 if(!textdate(member(cur,"time"),time,16)||!number(member(cur,"temperature_2m"),&temp)||!number(member(cur,"relative_humidity_2m"),&hum)||!number(member(cur,"wind_speed_10m"),&wind)||!number(member(cur,"weather_code"),&code))return 2;
 for(int i=0;i<4;i++){
  if(!textdate(element(member(daily,"time"),i),dates[i],10)||!number(element(member(daily,"temperature_2m_max"),i),&hi[i])||!number(element(member(daily,"temperature_2m_min"),i),&lo[i])||!number(element(member(daily,"weather_code"),i),&codes[i]))return 2;
  if(lo[i]<-100||hi[i]>100||lo[i]>hi[i]||codes[i]<0||codes[i]>99||codes[i]!=(int)codes[i])return 2;
  if(i&&strcmp(dates[i-1],dates[i])>=0)return 2;
 }
 if(strncmp(time,dates[0],10)||temp<-100||temp>100||hum<0||hum>100||wind<0||wind>200||code<0||code>99||code!=(int)code)return 2;
 printf("current|%s|%g|%g|%g|%.0f|%g|%g\n",time,temp,hum,wind,code,hi[0],lo[0]);
 for(int i=1;i<4;i++)printf("forecast|%s|%.0f|%g|%g\n",dates[i],codes[i],hi[i],lo[i]);
 return 0;
}
