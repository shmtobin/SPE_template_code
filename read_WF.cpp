#include <cstdio>
#include <iostream>
#include <fstream>
#include <vector>
#include <string>
#include <sstream>

using namespace std;

struct MQWaveform {
    int run, evt, chan, ipulse, iStart, iMax;
    float tStart, tStep;
    vector<int> V;

    void CalcMinMax() {
        if (V.empty()) return;
        int minVal = V[0], maxVal = V[0];
        for (int val : V) {
            if (val < minVal) minVal = val;
            if (val > maxVal) maxVal = val;
        }
         
    }
};

int main(int argc, char* argv[]) {
    if (argc < 2) {
        cerr << "Usage: " << argv[0] << " <run_number>\n";
        return 1;
    }

    int rnum;
    stringstream ss(argv[1]);
    ss >> rnum;

    if (ss.fail()) {
        cerr << "Invalid run number provided.\n";
        return 1;
    }

    stringstream fNameSS;
    fNameSS << "Run" << rnum << "_WF.ant";
    string fName = fNameSS.str();

    FILE* f = fopen(fName.c_str(), "r");
    if (!f) {
        cerr << "Could not open " << fName << "\n";
        return 1;
    }
    cout << "Opened file: " << fName << "\n";

    vector<MQWaveform> Wfs;
    int k = 1;

     cout << "Computing min and max values for all waveforms...\n";

    while (k > 0) {
        MQWaveform wf;
        int _run, _evt, _chan, _ipulse, _iStart;
        k = fscanf(f, "%d %d %d %d %d", &_run, &_evt, &_chan, &_ipulse, &_iStart);
        if (k > 0) {
            if (_run != rnum)
                cerr << "Run number mismatch. Read " << _run << " but expected " << rnum << "\n";
            wf.run = _run;
            wf.evt = _evt;
            wf.chan = _chan;
            wf.ipulse = _ipulse;
            wf.iStart = _iStart;

            float fval;
            k = fscanf(f, "%f", &fval);
            wf.tStart = fval;
            k = fscanf(f, "%f", &fval);
            wf.tStep = fval;

            int nSamp;
            k = fscanf(f, "%d", &nSamp);
            wf.iMax = 0;
            int VMax = -99999;
            for (int i = 0; i < nSamp; i++) {
                int _ival;
                k = fscanf(f, " %d", &_ival);
                wf.V.push_back(_ival);
                if (_ival > VMax) {
                    VMax = _ival;
                    wf.iMax = i;
                }
            }
            wf.CalcMinMax();
            Wfs.push_back(wf);
        }
    }
    fclose(f);

    cout << "Read " << Wfs.size() << " waveforms.\n";

    // Construct CSV filename
    stringstream outNameSS;
    outNameSS << "Run" << rnum << "_waveforms.csv";
    string outName = outNameSS.str();

    ofstream outFile(outName);
    if (!outFile) {
        cerr << "Error creating CSV file.\n";
        return 1;
    }

    outFile << "waveform_index, time (ns), voltage (mV)\n";

    for (size_t j = 0; j < Wfs.size(); j++) {
        MQWaveform& wf = Wfs[j];
        for (size_t i = 0; i < wf.V.size(); i++) {
            float time = wf.tStart + wf.tStep * i;
            float voltage = wf.V[i] / 10.0;
            outFile << j << ", " << time << ", " << voltage << "\n";
        }
    }
    outFile.close();
    cout << "CSV file '" << outName << "' created with all waveforms.\n";

    return 0;
}