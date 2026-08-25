#include <cstdio>
#include <iostream>
#include <fstream>
#include <vector>
#include <string>
#include <sstream>
#include <cmath>
 
using namespace std;
 
struct MQSPulse {
    int run, evt, chan, ipulse, fitnpoints, qual;
    float V, area, time, fittime, fitdtime;
    float halftime, fitslope, fitprob;
    float width, sidebandMean, sidebandRMS;
    float risetime, falltime, premean, prerms;
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
    fNameSS << "Run" << rnum << "_mqspulses.ant";
    string fName = fNameSS.str();
 
    ifstream in(fName);
    if (!in) {
        cerr << "Could not open " << fName << "\n";
        return 1;
    }
    cout << "Opened file: " << fName << "\n";
 
    vector<MQSPulse> pulses;
    string line;
    while (std::getline(in, line)) {
        if (line.empty()) continue;
 
        // split tokens by whitespace
        istringstream iss(line);
        vector<string> tok;
        string t;
        while (iss >> t) {
            // remove possible Windows CR at end of token
            if (!t.empty() && t.back() == '\r') t.pop_back();
            tok.push_back(t);
        }
 
        // Need at least 21 tokens to fill the expected CSV columns
        if (tok.size() < 21) {
            // skip malformed/short lines
            continue;
        }
 
        MQSPulse p;
        // Map tokens (0-based) from .ant to struct fields.
        // If .ant has extra trailing values they are ignored.
        try {
            p.run = std::stoi(tok[0]);
            p.evt = std::stoi(tok[1]);
            p.chan = std::stoi(tok[2]);
 
            p.V = std::stof(tok[3]);
            p.area = std::stof(tok[4]);
            p.time = std::stof(tok[5]);
            p.fittime = std::stof(tok[6]);
            p.fitdtime = std::stof(tok[7]);
 
            p.halftime = std::stof(tok[8]);
            p.fitslope = std::stof(tok[9]);
 
            // Fit npoints and fitprob may be stored as numeric tokens;
            // fitnpoints is integer, fitprob float
            p.fitnpoints = (int)std::lround(std::stof(tok[10]));
            p.fitprob = std::stof(tok[11]);
 
            p.ipulse = (int)std::lround(std::stof(tok[12]));
            p.width = std::stof(tok[13]);
            p.sidebandMean = std::stof(tok[14]);
            p.sidebandRMS = std::stof(tok[15]);
 
            p.qual = (int)std::lround(std::stof(tok[16]));
            p.risetime = std::stof(tok[17]);
            p.falltime = std::stof(tok[18]);
            p.premean = std::stof(tok[19]);
            p.prerms = std::stof(tok[20]);
        } catch (const std::exception&) {
            // if any conversion fails, skip this line
            continue;
        }
 
        if (p.run != rnum) {
            cerr << "Run number mismatch: got " << p.run << ", expected " << rnum << "\n";
        }
 
        pulses.push_back(p);
    }
 
    in.close();
    cout << "Read " << pulses.size() << " pulses.\n";
 
    // Output CSV
    stringstream outNameSS;
    outNameSS << "Run" << rnum << "_mqspulses.csv";
    string outName = outNameSS.str();
 
    ofstream outFile(outName);
    if (!outFile) {
        cerr << "Error creating CSV file.\n";
        return 1;
    }
 
    // Write header
    outFile << "run,evt,chan,V,area,time,fittime,fitdtime,halftime,fitslope,"
            << "fitnpoints,fitprob,ipulse,width,sidebandMean,sidebandRMS,"
            << "qual,risetime,falltime,premean,prerms\n";
 
    // Write pulse data
    for (const MQSPulse& p : pulses) {
        outFile << p.run << "," << p.evt << "," << p.chan << ","
                << p.V << "," << p.area << "," << p.time << ","
                << p.fittime << "," << p.fitdtime << "," << p.halftime << ","
                << p.fitslope << "," << p.fitnpoints << "," << p.fitprob << ","
                << p.ipulse << "," << p.width << "," << p.sidebandMean << ","
                << p.sidebandRMS << "," << p.qual << "," << p.risetime << ","
                << p.falltime << "," << p.premean << "," << p.prerms << "\n";
    }
 
    outFile.close();
    cout << "CSV file '" << outName << "' created with all pulse entries.\n";
 
    return 0;
}