/*
 * Licensed to the OpenAirInterface (OAI) Software Alliance under one or more
 * contributor license agreements.  See the NOTICE file distributed with
 * this work for additional information regarding copyright ownership.
 * The OpenAirInterface Software Alliance licenses this file to You under
 * the OAI Public License, Version 1.1  (the "License"); you may not use this file
 * except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.openairinterface.org/?page_id=698
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *------------------------------------------------------------------------------
 * For more information about the OpenAirInterface (OAI) Software Alliance:
 *      contact@openairinterface.org
 */

/*! \file latseq.c
* \brief latency sequence tool
* \author Flavien Ronteix--Jacquet
* \date 2020
* \version 1.0
* @ingroup util
*/
#define _GNU_SOURCE // required for pthread_setname_np()
#include "latseq.h"

/*--- GLOBALS and EXTERNS ----------------------------------------------------*/

latseq_t g_latseq;
__thread latseq_thread_data_t tls_latseq = {
  .th_latseq_id = 0
}; // need to be a thread local storage variable.
pthread_t logger_thread;
pthread_t fflusher_thread;
//double cpuf; //cpu frequency in MHz -> usec. Should be initialized in main.c
extern volatile int oai_exit; //oai is ended. Close latseq

/*--- UTILS FUNCTIONS --------------------------------------------------------*/

uint64_t get_cpu_freq_cycles(void)
{
  uint64_t ts = l_rdtsc();
  sleep(1);
  return (l_rdtsc() - ts);
}

/*--- MAIN THREAD FUNCTIONS --------------------------------------------------*/

int init_latseq(const char * appname, uint64_t cpufreq)
{ 
  // init members
  g_latseq.is_running = 0;
  //synchronise time and rdtsc
  struct timespec ts;
  clock_gettime(CLOCK_REALTIME, &ts);
  g_latseq.time_zero = (uint64_t)ts.tv_sec * 1000000000LL + (uint64_t)ts.tv_nsec;
  g_latseq.rdtsc_zero = l_rdtsc(); //check at compile time that constant_tsc is enabled in /proc/cpuinfo
  if (cpufreq == 0) {
    g_latseq.cpu_freq = get_cpu_freq_cycles();
  } else {
    g_latseq.cpu_freq = cpufreq;
  }

  // Open traces
  char time_string[16];
  strftime(time_string, sizeof (time_string), "%d%m%Y_%H%M%S", localtime(&ts.tv_sec));
  g_latseq.filelog_name = (char *)malloc(LATSEQ_MAX_STR_SIZE);
  sprintf(g_latseq.filelog_name, "%s.%s.lseq", appname, time_string);
  //open logfile
  g_latseq.outstream = fopen(g_latseq.filelog_name, "w");
  if (g_latseq.outstream == NULL) {
    g_latseq.is_running = 0;
    printf("[LATSEQ] Error at opening log file\n");
    return -1;
  }
  //write header
  char hdr[] = "# LatSeq packet fingerprints\n# By Alexandre Ferrieux and Flavien Ronteix Jacquet\n# timestamp\tU/D\tsrc--dest\tlen:ctxtId:localId\n";
  size_t ret = fwrite(hdr, sizeof(char), sizeof(hdr) - 1, g_latseq.outstream);
  if (ret < 0) {
    printf("[LATSEQ] Error at opening log file\n");
    g_latseq.is_running = 0;
    return -1;
  }
  fprintf(g_latseq.outstream, "%ld S rdtsc--gettimeofday %ld.%09ld\n", g_latseq.rdtsc_zero, ts.tv_sec, ts.tv_nsec);
  fflush(g_latseq.outstream);
  
  // init registry
  g_latseq.local_log_buffers.read_ith_thread = 0;
  g_latseq.local_log_buffers.nb_th = 0;
  memset(&g_latseq.local_log_buffers.read_ith_thread, 0, MAX_NB_THREAD * sizeof(unsigned int));
  
  // init stat
  g_latseq.stats.entry_counter = 0;
  g_latseq.stats.bytes_counter = 0;

  // init latseq_thread_t
  tls_latseq.th_latseq_id = 0;
  
  // init logger thread
  g_latseq.is_running = 1;
  
  return init_logger_latseq();
}

int init_logger_latseq(void)
{
  // init thread to write buffer to file
  if(pthread_create(&logger_thread, NULL, (void *) &latseq_log_to_file, NULL) > 0) {
    printf("[LATSEQ] Error at starting data collector\n");
    g_latseq.is_running = 0;
    return -1;
  }
  // init thread to flush into file
  pthread_create(&fflusher_thread, NULL, (void *) &fflush_latseq_periodically, NULL);

  return g_latseq.is_running;
}

void latseq_print_stats(void)
{
  printf("[LATSEQ] === stats ===\n");
  printf("[LATSEQ] number of entry in log : %d\n", g_latseq.stats.entry_counter);
  //printf("[LATSEQ] heads positions : %d (Write) : %d (Read)\n", g_latseq.i_write_head, g_latseq.i_read_head);
}

int close_latseq(void)
{
  g_latseq.is_running = 0;
  //Wait logger finish to write data
  pthread_join(logger_thread, NULL);
  //At this point, data_ids and points should be freed by the logger thread
  free((char*) g_latseq.filelog_name);
  if (fclose(g_latseq.outstream)){
    fprintf(stderr, "[LATSEQ] error on closing %s\n", g_latseq.filelog_name);
    exit(EXIT_FAILURE);
  }
  return 1;
}

/*--- INSTRUMENTED THREAD FUNCTIONS ------------------------------------------*/

int init_thread_for_latseq(void)
{

  //Init tls_latseq for local thread
  tls_latseq.i_write_head = 0; //local thread tls_latseq
  //memset(tls_latseq.log_buffer, 0, sizeof(tls_latseq.log_buffer));

  //Register thread in the registry
  latseq_registry_t * reg = &g_latseq.local_log_buffers;
  //Check if space left in registry
  if (reg->nb_th >= MAX_NB_THREAD) {
    g_latseq.is_running = 0;
    fprintf(g_latseq.outstream, "Max instrumented thread MAX_NB_THREAD reached\n");
    return -1;
  }
  reg->tls[reg->nb_th] = &tls_latseq;
  reg->i_read_heads[reg->nb_th] = 0;

  //Give id to the thread
  reg->nb_th++;
  tls_latseq.th_latseq_id = reg->nb_th;
  return 0;
  //TODO : No destroy function ? What happens when thread is stopped and data had not been written in the log file ?
}

/*--- DATA COLLECTOR THREAD FUNCTIONS ----------------------------------------*/

static int write_latseq_entry(void)
{
  //reference to latseq_thread_data
  latseq_thread_data_t * th = g_latseq.local_log_buffers.tls[g_latseq.local_log_buffers.read_ith_thread];
  //read_head for this thread_data
  unsigned int * i_read_head = &g_latseq.local_log_buffers.i_read_heads[g_latseq.local_log_buffers.read_ith_thread];
  //reference to element to write
  latseq_element_t * e = &th->log_buffer[(*i_read_head)%RING_BUFFER_SIZE];

  char * tmps;
  //Convert latseq_element to a string
  tmps = calloc(LATSEQ_MAX_STR_SIZE, sizeof(char));
  //Write the data identifier, e.g. do the vsprintf() here and not at measure()
  //We put the first NB_DATA_IDENTIFIERS elements of array, even there are no NB_DATA_IDENTIFIERS element to write. sprintf will get the firsts...
  sprintf(
    tmps,
    e->format, 
    e->data_id[0],
    e->data_id[1],
    e->data_id[2],
    e->data_id[3],
    e->data_id[4],
    e->data_id[5],
    e->data_id[6],
    e->data_id[7],
    e->data_id[8],
    e->data_id[9],
    e->data_id[10],
    e->data_id[11],
    e->data_id[12],
    e->data_id[13],
    e->data_id[14],
    e->data_id[15]);

  // Write into file
  int ret = fprintf(g_latseq.outstream, "%ld %s %s\n",
    e->ts,
    e->point,
    tmps);

  if (ret < 0) {
    g_latseq.is_running = 0;
    fclose(g_latseq.outstream);
    fprintf(stderr, "[LATSEQ] output log file cannot be written\n");
    exit(EXIT_FAILURE);
  }
#ifdef LATSEQ_DEBUG
  fprintf(g_latseq.outstream, "# debug %ld.%06ld : log an entry (len %d) for %s\n", etv.tv_sec, etv.tv_usec, ret, e->point);
  fprintf(g_latseq.outstream, "# info %ld.%06ld : buffer occupancy (%d / %d) for thread which embedded %s\n",etv.tv_sec, etv.tv_usec, OCCUPANCY((*(&th->i_write_head)%RING_BUFFER_SIZE), ((*i_read_head)%RING_BUFFER_SIZE)), RING_BUFFER_SIZE, e->point);
#endif

  free(tmps);
  // cleanup buffer element
  e->ts = 0;
  memset(e->data_id, 0, (sizeof(uint32_t) * e->len_id));
  e->len_id = 0;
  
  //Update read_head for the current read_ith_thread
  //Update g_latseq.local_log_buffers.i_read_heads[g_latseq.local_log_buffers.read_ith_thread] head position
  (*i_read_head)++;

  return ret;
}

void latseq_log_to_file(void)
{
  // pthread config
  pthread_t thId = pthread_self();
  //set name
  pthread_setname_np(thId, "latseq_log_to_file");
  //set priority
  int prio_for_policy = 10;
  pthread_setschedprio(thId, prio_for_policy);

  latseq_registry_t * reg = &g_latseq.local_log_buffers;
  int items_to_read = 0;

  while (!oai_exit) { // run until oai is stopped
    if (!g_latseq.is_running) { break; } //running flag is at 0, not running
    //If no thread registered, continue and wait
    if (reg->nb_th == 0) { usleep(1000); continue; }
    //Select a thread to read with read_ith_thread. 
    // Using RR for now, WRR in near future according to occupancy
    if (reg->read_ith_thread + 1 >= reg->nb_th) {
      reg->read_ith_thread = 0;
    } else {
      reg->read_ith_thread++;
    }

    //If max occupancy reached for a local buffer
    if (reg->tls[reg->read_ith_thread]->i_write_head < reg->i_read_heads[reg->read_ith_thread]) {
      fprintf(g_latseq.outstream, "# Error\tring buffer of thread (%d) reach max occupancy of %d\n", reg->read_ith_thread, RING_BUFFER_SIZE);
    }

    items_to_read = CHUNK_SIZE_ITEMS;
    // Write by chunk
    while (reg->tls[reg->read_ith_thread]->i_write_head > reg->i_read_heads[reg->read_ith_thread] && items_to_read > 0 ) {
      //printf("[debug] th %d : (%d)w (%d)r : (%d)items_to_read\n", reg->read_ith_thread, reg->tls[reg->read_ith_thread]->i_write_head, reg->i_read_heads[reg->read_ith_thread], items_to_read);
      items_to_read--;
      //Write pointed entry into log file
      g_latseq.stats.bytes_counter += (uint32_t)write_latseq_entry();
      g_latseq.stats.entry_counter++;
    }
    usleep(1);
  } // while(!oai_exit)

  //Write all remaining data
  for (uint8_t i = 0; i < reg->nb_th; i++) {
    reg->read_ith_thread = i;
    while (reg->tls[reg->read_ith_thread]->i_write_head > reg->i_read_heads[reg->read_ith_thread])
    {
      g_latseq.stats.bytes_counter += (uint32_t)write_latseq_entry();
      g_latseq.stats.entry_counter++;
    }
  }
  //close_latseq(); // function to close latseq properly
  //exit thread
  pthread_exit(NULL);
}

void fflush_latseq_periodically(void)
{
  struct timespec ts;
  while(1){
    sleep(1);
    fflush(g_latseq.outstream);
    clock_gettime(CLOCK_REALTIME, &ts);
    fprintf(g_latseq.outstream, "%ld S rdtsc--gettimeofday %ld.%09ld\n", l_rdtsc(), ts.tv_sec, ts.tv_nsec);
  }
  pthread_exit(NULL);
}
