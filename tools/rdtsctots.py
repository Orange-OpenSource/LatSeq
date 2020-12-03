#!/usr/bin/python3
import sys

# 78374 lines = 182ms; 1 line = 2.32us 

def usage():
    sys.stdout.write("[rdtsctots] ./rdtsctots.py raw_file.lseq > file.lseq")
    exit()

class rdtsctots():
    def __init__(self, filenameP):
        self.filename = filenameP
        self.lines = None
        with open(self.filename, 'r') as f:
            self.lines = f.readlines()
        f.close()
        if not self.lines:
            raise IOError(f"{filenameP} not loaded")
        self._cleanup_and_sort()


    def self_converted_rdtsc(self) -> bool:
        return self.is_converted_rdtsc(self.lines[0])

    def is_converted_rdtsc(self, lineP) -> bool:
        """
            return False if rdtsc else True
        """
        return '.' in lineP.split()[0]

    def _cleanup_and_sort(self):
        # put all comments at begin
        # TODO : more flexible
        end_header_idx = 3
        self.header = self.lines[0:end_header_idx-1]
        # sort
        self.lines = sorted(self.lines[end_header_idx:-1])

    def _get_offset_cpufreq(self):
        first_S = next(l for l in self.lines if ' S ' in l).split()
        last_S = next(l for l in self.lines[::-1] if ' S ' in l).split()
        cycle_offset = int(first_S[0])
        time_offset = float(first_S[3])
        cpufreq = int((int(last_S[0]) - int(first_S[0]))/(float(last_S[3]) - float(first_S[3])))
        return (cycle_offset, time_offset, cpufreq)
    
    def yield_rdtsctots(self):
        if self.self_converted_rdtsc():
            return
        offset, time0, cpufreq = self._get_offset_cpufreq()
        for l in self.lines:  # Compute and replace rdtsc value by gettimeofday
            tmp = l.split(" ", 1)
            yield f"%.6f {tmp[1]}" % ((int(tmp[0]) - offset)/cpufreq + time0)
    
    def write_rdtsctots(self, outfilename):
        if self.self_converted_rdtsc():
            return
        with open(outfilename, 'w+') as f:
            f.writelines(self.header)
            f.writelines(self.yield_rdtsctots())
        f.close()
    
if __name__ == "__main__":
    if len(sys.argv) != 2:
        usage()

    ro = rdtsctots(sys.argv[1])
    sys.stdout.writelines(ro.yield_rdtsctots())
