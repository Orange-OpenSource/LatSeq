#ifndef __LATSEQ_H__
#define __LATSEQ_H__

/*--- INCLUDES ---------------------------------------------------------------*/
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <syslog.h>
#include <assert.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <fcntl.h>
#include <stdarg.h>
#include <time.h>
#include <stdint.h>
#ifndef __STDC_FORMAT_MACROS
  #define __STDC_FORMAT_MACROS
#endif
#include <inttypes.h>
#ifndef _GNU_SOURCE
  #define _GNU_SOURCE
#endif
#include <pthread.h>
//#include <T.h>
#include <utils.h>
#include <LOG/log.h>
#include <openair1/PHY/TOOLS/time_meas.h>


/*----------------------------------------------------------------------------*/

/*--- DEFINE -----------------------------------------------------------------*/

#define MAX_LOG_SIZE        32
#define MAX_LOG_OCCUPANCY   24 // Should be < MAX_LOG_OCCUPANCY
#define MAX_POINT_NAME_SIZE 32
#define MAX_NAME_SIZE       64
//#define MAX_LEN_DATA_ID     12 //correspond to name + value. value might be represent with 6 chars
#define MAX_NB_DATA_ID      16
#define NB_DATA_IDENTIFIERS 10 // to update according to distinct data identifier used in point
#define MAX_SIZE_LINE_OF_LOG 128 // ts=8c + pointname=MAX_POINT_NAME_SIZEc + identifier=NB_DATA_IDENTIFIERx(4c name + 4c number) (Worst-case)

#define LATSEQ_P3(p, f, i1) do {log_measure1(p, f, i1); } while(0)
#define LATSEQ_P4(p, f, i1, i2) do {log_measure2(p, f, i1, i2); } while(0)
#define LATSEQ_P5(p, f, i1, i2, i3) do {log_measure3(p, f, i1, i2, i3); } while(0)
#define LATSEQ_P6(p, f, i1, i2, i3, i4) do {log_measure4(p, f, i1, i2, i3, i4);} while(0)
#define LATSEQ_P7(p, f, i1, i2, i3, i4, i5) do {log_measure5(p, f, i1, i2, i3, i4, i5); } while(0)
#define LATSEQ_P8(p, f, i1, i2, i3, i4, i5, i6) do {log_measure6(p, f, i1, i2, i3, i4, i5, i6); } while(0)
#define LATSEQ_P9(p, f, i1, i2, i3, i4, i5, i6, i7) do {log_measure7(p, f, i1, i2, i3, i4, i5, i6, i7); } while(0)
#define LATSEQ_P10(p, f, i1, i2, i3, i4, i5, i6, i7, i8) do {log_measure8(p, f, i1, i2, i3, i4, i5, i6, i7, i8); } while(0)
#define LATSEQ_P11(p, f, i1, i2, i3, i4, i5, i6, i7, i8, i9) do {log_measure9(p, f, i1, i2, i3, i4, i5, i6, i7, i8, i9); } while(0)
#define LATSEQ_P12(p, f, i1, i2, i3, i4, i5, i6, i7, i8, i9, i10) do {log_measure10(p, f, i1, i2, i3, i4, i5, i6, i7, i8, i9, i10); } while(0)

#define GET_MACRO(_1,_2,_3,_4,_5,_6,_7,_8,_9,_10,_11,_12,NAME,...) NAME
#define LATSEQ_P(...) GET_MACRO(__VA_ARGS__, LATSEQ_P12, LATSEQ_P11, LATSEQ_P10, LATSEQ_P9, LATSEQ_P8, LATSEQ_P7, LATSEQ_P6, LATSEQ_P5, LATSEQ_P4, LATSEQ_P3)(__VA_ARGS__)



#define OCCUPANCY(w, r) (w - r)

#define MAX_NB_THREAD 32

/*--- STRUCT -----------------------------------------------------------------*/

// A latseq element of the buffer
typedef struct latseq_element_t {
  uint64_t            ts; // timestamp of the measure
  const char *        point;
  //char                point[MAX_POINT_NAME_SIZE]; // point name
  const char *        format;
  //char *              format; // format for the data identifier
  short               len_id; // Number data identifiers
  uint32_t            data_id[MAX_NB_DATA_ID]; // values for the data identifier. What is the best type ?
} latseq_element_t;

// Statistics structures for latseq
typedef struct latseq_stats_t {
  unsigned int        entry_counter;
} latseq_stats_t;

//thread specific data struct
typedef struct latseq_thread_data_t {
  uint8_t             th_latseq_id; //Identifier of pthread for registry
  latseq_element_t    log_buffer[MAX_LOG_SIZE]; //log buffer, structure mutex-less
  unsigned int        i_write_head; // position of writer in the log_buffer (main thread)
} latseq_thread_data_t;

//Registry of pointers to thread-specific struct latseq_data_thread
typedef struct latseq_registry_t {
  uint8_t                 read_ith_thread;
  uint8_t                 nb_th;
  latseq_thread_data_t *  tls[MAX_NB_THREAD];
  unsigned int            i_read_heads[MAX_NB_THREAD]; // position of reader in the ith log buffer (logger thread)
} latseq_registry_t;

// Global structure of LatSeq module
typedef struct latseq_t {
  int                 is_running; //1 is running, 0 not running
  int                 is_debug; //1 debug, 0 prod
  char *              filelog_name;
  FILE *              outstream; //Output descriptor
  struct timeval      time_zero; // time zero
  uint64_t            rdtsc_zero; //rdtsc zero
  latseq_registry_t   local_log_buffers; //Register of thread-specific buffers
  latseq_stats_t      stats; // stats of latseq instance
} latseq_t;

/*--- EXTERNS ----------------------------------------------------------------*/

extern latseq_t g_latseq; // global structure
extern __thread latseq_thread_data_t tls_latseq;

/*--- FUNCTIONS --------------------------------------------------------------*/
/** \fn int init_latseq(const char * appname, int debug);
 * \brief init latency sequences module.
 * \param appname app's name. The output file is appname.date_hour.lseq
 * \param debug level for this instance of latseq
 * \return 0 if error 1 otherwise
*/
int init_latseq(const char * appname, int debug);

/** \fn init_logger_to_mem(void);
 * \brief init thread logger
*/
void init_logger_latseq(void);

/** \fn init_thread_for_latseq(void);
 * \brief init tls_latseq for local oai thread
 * \return -1 if error, 0 otherwise
*/
int init_thread_for_latseq(void);

/** \fn void log_measure(const char * point, const char *identifier);
 * \brief function to log a new measure into buffer
 * \param point name of the measurement point
 * \param id identifier for the data pointed
 * \todo  measure latency introduced by this function
*/
//static __inline__ void log_measure1(const char * point, const char *fmt, ...)
static __inline__ void log_measure1(const char * point, const char *fmt, uint32_t i1)
{
  /*
#ifdef LATSEQ_DEBUG
  struct timeval begin, end;
  gettimeofday(&begin, NULL);
#endif
*/
  //TODO : chack that latseq is running
  //check if the oai thread is already registered
  if (tls_latseq.th_latseq_id == 0) {
    //is not initialized yet
    if (init_thread_for_latseq()) {
      return;
    }
  }
  // No check here because it will be check by the reader
  //get list of argument
  //va_list va;
  //va_start(va, fmt); //start all values after fmt

  //get reference on new element
  latseq_element_t * e = &tls_latseq.log_buffer[tls_latseq.i_write_head%MAX_LOG_SIZE];

  //Log time
  e->ts = rdtsc(); //Not used because rdtsc from log.h seems to be not static
  //e->ts = rdtsc_oai(); //use of rdtsc defined in time_meas.h
  //unsigned long long a, d;
  //__asm__ volatile ("rdtsc" : "=a" (a), "=d" (d));
  //e->ts = (d<<32) | a; //because of imcompatibility between inline and static of rdtsc. Assumption : usage of __x86_64__

  //Log point name
  //strcpy(e->point, point);
  e->point = point;
  e->format = fmt;

  //Log data identifier
  //e->len_id = 0;
  e->len_id = 1;
  //while ( (e->data_id[e->len_id] = (uint32_t)va_arg(va, int) )!= -1)
  //  e->len_id++;
  //becareful, the data_id[e->len_id + 1] = (uint32_t)-1. Use len_id to know the correct number of element
  e->data_id[0] = i1;
  
  //Update head position
  tls_latseq.i_write_head++;
  //Clean up va_list
  //va_end(va);
  /*
#ifdef LATSEQ_DEBUG
  gettimeofday(&end, NULL);
  printf("[LATSEQ] log_measure took : 06%lu us\n", (end.tv_usec - begin.tv_usec)); //at 23-03, 60usec
#endif
*/
}

static __inline__ void log_measure2(const char * point, const char *fmt, uint32_t i1, uint32_t i2)
{
  if (tls_latseq.th_latseq_id == 0) {
    //is not initialized yet
    if (init_thread_for_latseq()) {
      return;
    }
  }
  latseq_element_t * e = &tls_latseq.log_buffer[tls_latseq.i_write_head%MAX_LOG_SIZE];
  e->ts = rdtsc();
  e->point = point;
  e->format = fmt;
  e->len_id = 2;
  e->data_id[0] = i1;
  e->data_id[1] = i2;
  tls_latseq.i_write_head++;
}

static __inline__ void log_measure3(const char * point, const char *fmt, uint32_t i1, uint32_t i2, uint32_t i3)
{
  if (tls_latseq.th_latseq_id == 0) {
    //is not initialized yet
    if (init_thread_for_latseq()) {
      return;
    }
  }
  latseq_element_t * e = &tls_latseq.log_buffer[tls_latseq.i_write_head%MAX_LOG_SIZE];
  e->ts = rdtsc();
  e->point = point;
  e->format = fmt;
  e->len_id = 3;
  e->data_id[0] = i1;
  e->data_id[1] = i2;
  e->data_id[2] = i3;
  tls_latseq.i_write_head++;
}

static __inline__ void log_measure4(const char * point, const char *fmt, uint32_t i1, uint32_t i2, uint32_t i3, uint32_t i4)
{
  if (tls_latseq.th_latseq_id == 0) {
    //is not initialized yet
    if (init_thread_for_latseq()) {
      return;
    }
  }
  latseq_element_t * e = &tls_latseq.log_buffer[tls_latseq.i_write_head%MAX_LOG_SIZE];
  e->ts = rdtsc();
  e->point = point;
  e->format = fmt;
  e->len_id = 4;
  e->data_id[0] = i1;
  e->data_id[1] = i2;
  e->data_id[2] = i3;
  e->data_id[3] = i4;
  tls_latseq.i_write_head++;
}

static __inline__ void log_measure5(const char * point, const char *fmt, uint32_t i1, uint32_t i2, uint32_t i3, uint32_t i4, uint32_t i5)
{
  if (tls_latseq.th_latseq_id == 0) {
    //is not initialized yet
    if (init_thread_for_latseq()) {
      return;
    }
  }
  latseq_element_t * e = &tls_latseq.log_buffer[tls_latseq.i_write_head%MAX_LOG_SIZE];
  e->ts = rdtsc();
  e->point = point;
  e->format = fmt;
  e->len_id = 5;
  e->data_id[0] = i1;
  e->data_id[1] = i2;
  e->data_id[2] = i3;
  e->data_id[3] = i4;
  e->data_id[4] = i5;
  tls_latseq.i_write_head++;
}

static __inline__ void log_measure6(const char * point, const char *fmt, uint32_t i1, uint32_t i2, uint32_t i3, uint32_t i4, uint32_t i5, uint32_t i6)
{
  if (tls_latseq.th_latseq_id == 0) {
    //is not initialized yet
    if (init_thread_for_latseq()) {
      return;
    }
  }
  latseq_element_t * e = &tls_latseq.log_buffer[tls_latseq.i_write_head%MAX_LOG_SIZE];
  e->ts = rdtsc();
  e->point = point;
  e->format = fmt;
  e->len_id = 6;
  e->data_id[0] = i1;
  e->data_id[1] = i2;
  e->data_id[2] = i3;
  e->data_id[3] = i4;
  e->data_id[4] = i5;
  e->data_id[5] = i6;
  tls_latseq.i_write_head++;
}


static __inline__ void log_measure7(const char * point, const char *fmt, uint32_t i1, uint32_t i2, uint32_t i3, uint32_t i4, uint32_t i5, uint32_t i6, uint32_t i7)
{
  if (tls_latseq.th_latseq_id == 0) {
    //is not initialized yet
    if (init_thread_for_latseq()) {
      return;
    }
  }
  latseq_element_t * e = &tls_latseq.log_buffer[tls_latseq.i_write_head%MAX_LOG_SIZE];
  e->ts = rdtsc();
  e->point = point;
  e->format = fmt;
  e->len_id = 7;
  e->data_id[0] = i1;
  e->data_id[1] = i2;
  e->data_id[2] = i3;
  e->data_id[3] = i4;
  e->data_id[4] = i5;
  e->data_id[5] = i6;
  e->data_id[6] = i7;
  tls_latseq.i_write_head++;
}


static __inline__ void log_measure8(const char * point, const char *fmt, uint32_t i1, uint32_t i2, uint32_t i3, uint32_t i4, uint32_t i5, uint32_t i6, uint32_t i7, uint32_t i8)
{
  if (tls_latseq.th_latseq_id == 0) {
    //is not initialized yet
    if (init_thread_for_latseq()) {
      return;
    }
  }
  latseq_element_t * e = &tls_latseq.log_buffer[tls_latseq.i_write_head%MAX_LOG_SIZE];
  e->ts = rdtsc();
  e->point = point;
  e->format = fmt;
  e->len_id = 8;
  e->data_id[0] = i1;
  e->data_id[1] = i2;
  e->data_id[2] = i3;
  e->data_id[3] = i4;
  e->data_id[4] = i5;
  e->data_id[5] = i6;
  e->data_id[6] = i7;
  e->data_id[7] = i8;
  tls_latseq.i_write_head++;
}


static __inline__ void log_measure9(const char * point, const char *fmt, uint32_t i1, uint32_t i2, uint32_t i3, uint32_t i4, uint32_t i5, uint32_t i6, uint32_t i7, uint32_t i8, uint32_t i9)
{
  if (tls_latseq.th_latseq_id == 0) {
    //is not initialized yet
    if (init_thread_for_latseq()) {
      return;
    }
  }
  latseq_element_t * e = &tls_latseq.log_buffer[tls_latseq.i_write_head%MAX_LOG_SIZE];
  e->ts = rdtsc();
  e->point = point;
  e->format = fmt;
  e->len_id = 9;
  e->data_id[0] = i1;
  e->data_id[1] = i2;
  e->data_id[2] = i3;
  e->data_id[3] = i4;
  e->data_id[4] = i5;
  e->data_id[5] = i6;
  e->data_id[6] = i7;
  e->data_id[7] = i8;
  e->data_id[8] = i9;
  tls_latseq.i_write_head++;
}


static __inline__ void log_measure10(const char * point, const char *fmt, uint32_t i1, uint32_t i2, uint32_t i3, uint32_t i4, uint32_t i5, uint32_t i6, uint32_t i7, uint32_t i8, uint32_t i9, uint32_t i10)
{
  if (tls_latseq.th_latseq_id == 0) {
    //is not initialized yet
    if (init_thread_for_latseq()) {
      return;
    }
  }
  latseq_element_t * e = &tls_latseq.log_buffer[tls_latseq.i_write_head%MAX_LOG_SIZE];
  e->ts = rdtsc();
  e->point = point;
  e->format = fmt;
  e->len_id = 10;
  e->data_id[0] = i1;
  e->data_id[1] = i2;
  e->data_id[2] = i3;
  e->data_id[3] = i4;
  e->data_id[4] = i5;
  e->data_id[5] = i6;
  e->data_id[6] = i7;
  e->data_id[7] = i8;
  e->data_id[8] = i9;
  e->data_id[9] = i10;
  tls_latseq.i_write_head++;
}

/** \fn static int write_latseq_entry(void);
 * \brief private function to write an entry in the log file
*/
//static int write_latseq_entry(void);

/** \fn void log_to_file(void);
 * \brief function to save buffer of logs into a file
*/
void latseq_log_to_file(void);

/** \fn void latseq_print_stats(void);
 * \brief print some stats about latseq
*/
void latseq_print_stats(void);

/** \fn int close_latseq(void);
 * \brief finish latseq measurement if a latseq is running
 * \return 0 if error 1 otherwise
*/
int close_latseq(void);

/*----------------------------------------------------------------------------*/

#endif
