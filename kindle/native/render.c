/* InkDesk offscreen renderer. PGM output avoids framebuffer text and rotation APIs. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#define STB_IMAGE_IMPLEMENTATION
#define STBI_ONLY_PNG
#include "vendor/stb_image.h"
#define STB_TRUETYPE_IMPLEMENTATION
#include "vendor/stb_truetype.h"
static unsigned char *canvas;
static int W,H;
static void pixel(int x,int y,int value) {
 if(x>=0&&x<W&&y>=0&&y<H) canvas[y*W+x]=(unsigned char)value;
}
static int utf8(const unsigned char **s) {
 unsigned int c=*(*s)++;
 if(c<128)return (int)c;
 int n=c<224?1:c<240?2:3;c&=(1u<<(6-n))-1;
 while(n-- && **s){c=(c<<6)|(*(*s)++ & 63);}
 return (int)c;
}
static unsigned char *readfont(const char *path) {
 FILE *f=fopen(path,"rb");if(!f)return NULL;
 if(fseek(f,0,SEEK_END)){fclose(f);return NULL;}long n=ftell(f);rewind(f);
 if(n<=0||n>64000000){fclose(f);return NULL;}
 unsigned char *p=malloc((size_t)n);if(!p){fclose(f);return NULL;}
 if(fread(p,1,(size_t)n,f)!=(size_t)n){free(p);p=NULL;}fclose(f);return p;
}
static void text(stbtt_fontinfo *font,int size,int y,int x,int color,const char *s) {
 float scale=stbtt_ScaleForMappingEmToPixels(font,(float)size);
 const unsigned char *p=(const unsigned char*)s;
 int miny=10000,advance=0,previous=0;
 /* Match the existing layout's top-margin compensation, but center glyphs
    against a stable font cap height so different digits do not jump. */
 int bx0,by0,bx1,by1;
 stbtt_GetCodepointBitmapBox(font,'0',scale,scale,&bx0,&by0,&bx1,&by1);
 miny=by0;
 int baseline=y+(size*45/100)-miny;
 while(*p) {
  int c=utf8(&p),ax,lsb;
  if(previous)advance+=(int)lroundf(stbtt_GetCodepointKernAdvance(font,previous,c)*scale);
  int width,height,dx,dy;
  unsigned char *bitmap=stbtt_GetCodepointBitmap(font,scale,scale,c,&width,&height,&dx,&dy);
  if(bitmap) {
   for(int yy=0;yy<height;yy++)for(int xx=0;xx<width;xx++) {
    int tx=x+advance+dx+xx,ty=baseline+dy+yy;
    if(tx>=0&&tx<W&&ty>=0&&ty<H) {
     int a=bitmap[yy*width+xx],old=canvas[ty*W+tx];
     pixel(tx,ty,(old*(255-a)+color*a+127)/255);
    }
   }
   stbtt_FreeBitmap(bitmap,NULL);
  }
  stbtt_GetCodepointHMetrics(font,c,&ax,&lsb);
  advance+=(int)lroundf(ax*scale);previous=c;
 }
}
static int text_width(stbtt_fontinfo *font,int size,const char *s) {
 float scale=stbtt_ScaleForMappingEmToPixels(font,(float)size);
 const unsigned char *p=(const unsigned char*)s;int width=0,previous=0;
 while(*p){int c=utf8(&p),a,b;stbtt_GetCodepointHMetrics(font,c,&a,&b);
  if(previous)width+=(int)lroundf(stbtt_GetCodepointKernAdvance(font,previous,c)*scale);
  width+=(int)lroundf(a*scale);previous=c;}
 return width;
}
static int picture(const char *path,int x,int y,int w,int h) {
 int iw,ih,n;unsigned char *im=stbi_load(path,&iw,&ih,&n,1);
 if(!im){fprintf(stderr,"render: image missing: %s\n",path);return 1;}
 if(w<=0)w=iw;if(h<=0)h=ih;
 for(int yy=0;yy<h;yy++)for(int xx=0;xx<w;xx++)pixel(x+xx,y+yy,im[(yy*ih/h)*iw+xx*iw/w]);
 stbi_image_free(im);return 0;
}
int main(int argc,char **argv) {
 if(argc!=8){fprintf(stderr,"usage: render width height rotate font commands output clock-only\n");return 2;}
 W=atoi(argv[1]);H=atoi(argv[2]);int rotate=atoi(argv[3]),partial=atoi(argv[7]);
 if(W<=0||H<=0||W>2048||H>2048)return 2;
 canvas=malloc((size_t)W*H);if(!canvas)return 2;memset(canvas,255,(size_t)W*H);
 unsigned char *fontdata=readfont(argv[4]);stbtt_fontinfo font;
 if(!fontdata||!stbtt_InitFont(&font,fontdata,stbtt_GetFontOffsetForIndex(fontdata,0))){fprintf(stderr,"render: invalid font\n");return 2;}
 FILE *input=fopen(argv[5],"r");if(!input)return 2;
 char *line=NULL;size_t cap=0;int errors=0;
 while(getline(&line,&cap,input)>0) {
  line[strcspn(line,"\r\n")]=0;char *save=NULL,*kind=strtok_r(line,"|",&save);
  if(!kind)continue;int a[5];int count=kind[0]=='T'||kind[0]=='M'?4:kind[0]=='I'?4:5;
  int ok=1;for(int i=0;i<count;i++){char *v=strtok_r(NULL,"|",&save);if(!v){ok=0;break;}a[i]=atoi(v);}if(!ok){errors++;continue;}
  if(kind[0]=='T'||kind[0]=='M') {
   if(!save||!*save)continue;
   int x=kind[0]=='M'?(W-text_width(&font,a[0],save))/2:a[2];
   text(&font,a[0],a[1],x,a[3],save);
  }else if(kind[0]=='I') {
   if(save&&*save)errors+=picture(save,a[0],a[1],a[2],a[3]);
  }else if(kind[0]=='R') {
   for(int yy=a[1];yy<a[1]+a[3];yy++)for(int xx=a[0];xx<a[0]+a[2];xx++)pixel(xx,yy,a[4]);
  }
 }
 fclose(input);free(line);
 if(errors){free(canvas);free(fontdata);return 1;}
 /* The supplied clock rectangle is intentionally fixed by layout. */
 int x=0,y=0,w=W,h=H;
 if(partial){if(rotate){x=40;y=156;w=640;h=244;}else{x=40;y=138;w=508;h=222;}}
 FILE *out=fopen(argv[6],"wb");if(!out)return 2;
 if(rotate){
  fprintf(out,"P5\n%d %d\n255\n",h,w);
  for(int xx=x+w-1;xx>=x;xx--)for(int yy=y;yy<y+h;yy++)fputc(canvas[yy*W+xx],out);
 }else{
  fprintf(out,"P5\n%d %d\n255\n",w,h);
  for(int yy=y;yy<y+h;yy++)fwrite(canvas+yy*W+x,1,(size_t)w,out);
 }
 int rc=fclose(out);free(canvas);free(fontdata);return rc?1:0;
}
