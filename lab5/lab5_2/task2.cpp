#include <iostream>
#include <vector>
#include <thread>
#include <mutex>
#include <random>
#include <algorithm>
#include <atomic>
#include <memory>
#include <set>
#include <iomanip>

using namespace std;

// Generates an undirected random graph.
vector<vector<int>> generateUndirectedGraph(int V, int E) {
    vector<vector<int>> graph(V);
    mt19937 gen(42);
    uniform_int_distribution<> disV(0, V - 1);

    // Backbone path to ensure connectivity: 0-1-2-...-V-1
    for (int i = 1; i < V; ++i) {
        graph[i - 1].push_back(i);
        graph[i].push_back(i - 1);
    }

    int current_edges = V - 1;
    while (current_edges < E) {
        int u = disV(gen);
        int v = disV(gen);

        if (u != v) {
            // Check if edge already exists
            if (find(graph[u].begin(), graph[u].end(), v) == graph[u].end()) {
                graph[u].push_back(v);
                graph[v].push_back(u);
                current_edges++;
            }
        }
    }
    return graph;
}

// Helper to print graph
void printGraph(const vector<vector<int>>& graph) {
    cout << "\nGenerated Undirected Graph:\n";
    for (int v = 0; v < graph.size(); ++v) {
        cout << "Vertex " << setw(2) << v << " connects to: ";
        for (int u : graph[v]) {
            cout << u << " ";
        }
        cout << "\n";
    }
    cout << "\n\n";
}

// Worker thread logic
void worker(int thread_id, int V,
    const vector<vector<int>>& graph,
    vector<int>& colors,
    vector<unique_ptr<mutex>>& vertex_mutexes,
    atomic<int>& idle_attempts,
    atomic<int>& total_minimization_attempts,
    atomic<int>& successful_color_changes,
    atomic<bool>& is_running) {

    // Thread-local random generator
    mt19937 gen(1337 + thread_id);
    uniform_int_distribution<> disV(0, V - 1);

    // Threshold for termination: if we failed to change any color 
    // across all threads V * 10 times consecutively, we assume convergence.
    const int CONVERGENCE_THRESHOLD = V * 10;

    while (is_running.load()) {
        if (idle_attempts.load() > CONVERGENCE_THRESHOLD) {
            is_running.store(false);
            break;
        }

        int target_v = disV(gen);

        // Gather the target vertex and all its neighbors
        vector<int> lock_sequence;
        lock_sequence.push_back(target_v);
        for (int neighbor : graph[target_v]) {
            lock_sequence.push_back(neighbor);
        }

        // Sort the IDs to prevent deadlocks
        sort(lock_sequence.begin(), lock_sequence.end());

        // Acquire locks
        for (int v : lock_sequence) {
            vertex_mutexes[v]->lock();
        }

        // Calculate Minimal Excluded (MEX) color
        set<int> used_colors;
        for (int neighbor : graph[target_v]) {
            if (colors[neighbor] != -1) {
                used_colors.insert(colors[neighbor]);
            }
        }

        // Find the smallest non-negative integer NOT in used_colors
        int mex_color = 0;
        for (int c : used_colors) {
            if (c == mex_color) {
                mex_color++;
            }
            else {
                break;
            }
        }

        // Apply minimization and update statistics
        total_minimization_attempts.fetch_add(1);

        if (colors[target_v] != mex_color) {
            colors[target_v] = mex_color;
            // State changed! Reset the idle counter.
            idle_attempts.store(0);
            successful_color_changes.fetch_add(1);
        }
        else {
            // No change happened. Increment idle counter.
            idle_attempts.fetch_add(1);
        }

        // Release locks in reverse order
        for (auto it = lock_sequence.rbegin(); it != lock_sequence.rend(); ++it) {
            vertex_mutexes[*it]->unlock();
        }
    }
}

int main() {
    const int V = 15; // Number of vertices
    const int E = 25; // Number of edges
    const int num_threads = 4;

    cout << "Initializing Graph Generation...\n";
    auto graph = generateUndirectedGraph(V, E);
    printGraph(graph);

    // Colors initialized to -1 (uncolored)
    vector<int> colors(V, -1);

    // Use unique_ptr<mutex> because std::mutex is not copyable/movable
    vector<unique_ptr<mutex>> vertex_mutexes;
    for (int i = 0; i < V; ++i) {
        vertex_mutexes.push_back(make_unique<mutex>());
    }

    // Shared atomic statistics and state control
    atomic<int> idle_attempts(0);
    atomic<int> total_minimization_attempts(0);
    atomic<int> successful_color_changes(0);
    atomic<bool> is_running(true);

    cout << "Starting Parallel Local Minimization Coloring with " << num_threads << " threads...\n";

    vector<thread> threads;
    for (int i = 0; i < num_threads; ++i) {
        threads.emplace_back(worker, i, V, cref(graph), ref(colors),
            ref(vertex_mutexes), ref(idle_attempts),
            ref(total_minimization_attempts),
            ref(successful_color_changes), ref(is_running));
    }

    for (auto& t : threads) {
        t.join();
    }

    // Output Statistics and Results
    cout << "\nSTATISTICS:\n";
    cout << "Total Vertices (V)       : " << V << "\n";
    cout << "Total Edges (E)          : " << E << "\n";
    cout << "Worker Threads           : " << num_threads << "\n";
    cout << "Total Attempts           : " << total_minimization_attempts.load() << "\n";
    cout << "Successful Color Changes : " << successful_color_changes.load() << "\n";
    cout << "\n\n";

    cout << "Final Locally Optimal Coloring:\n";
    for (int i = 0; i < V; ++i) {
        cout << "Vertex " << setw(2) << i << " -> Color " << colors[i] << "\n";
    }

    // Verification step: check if coloring is actually valid
    bool is_valid = true;
    for (int v = 0; v < V; ++v) {
        for (int u : graph[v]) {
            if (colors[v] == colors[u]) {
                is_valid = false;
                break;
            }
        }
    }

    cout << "\nValidation: " << (is_valid ? "SUCCESS (No adjacent vertices share the same color)" : "FAILED") << "\n";

    return 0;
}