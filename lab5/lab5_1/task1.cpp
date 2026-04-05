#include <iostream>
#include <vector>
#include <thread>
#include <barrier>
#include <numeric>
#include <random>
#include <limits>
#include <iomanip>

using namespace std;

// Prevents integer overflow when adding weights
const int INF = numeric_limits<int>::max() / 2;

// Structure to represent an incoming edge to a vertex
struct IncomingEdge {
    int from;
    int weight;
};

// Generates a simple random directed graph where graph[v] contains all edges going INTO v
vector<vector<IncomingEdge>> generateGraph(int V, int E) {
    vector<vector<IncomingEdge>> graph(V);
    mt19937 gen(42);
    uniform_int_distribution<> disV(0, V - 1);
    uniform_int_distribution<> disW(1, 10); // Edge weights from 1 to 10

    // Backbone path 0 -> 1 -> ... -> V-1
    for (int i = 1; i < V; ++i) {
        graph[i].push_back({ i - 1, disW(gen) });
    }

    // Add remaining random edges
    for (int i = 0; i < E - (V - 1); ++i) {
        int u = disV(gen);
        int v = disV(gen);
        if (u != v) {
            graph[v].push_back({ u, disW(gen) });
        }
    }
    return graph;
}

// Helper function to print the generated graph
void printGraph(const vector<vector<IncomingEdge>>& graph) {
    cout << "\nGenerated Graph Structure (Incoming Edges)\n";
    for (int v = 0; v < graph.size(); ++v) {
        cout << "Vertex " << setw(2) << v << " receives from: ";
        if (graph[v].empty()) {
            cout << "[None - Source or Unreachable]";
        }
        else {
            for (const auto& edge : graph[v]) {
                cout << "(v" << edge.from << ", w=" << edge.weight << ") ";
            }
        }
        cout << "\n";
    }
    cout << "\n\n";
}

// Worker function for each thread
void worker(int thread_id, int start_v, int end_v, int V,
    const vector<vector<IncomingEdge>>& graph,
    vector<vector<int>>& D,
    barrier<>& sync_barrier) {

    // Perform exactly N = |V| iterations
    for (int step = 0; step < V; ++step) {
        // Read from the current buffer and write to the next buffer.
        int current_idx = step % 2;
        int next_idx = (step + 1) % 2;

        // Process only the chunk of vertices assigned to this thread
        for (int v = start_v; v < end_v; ++v) {
            // Start with the current known minimum distance for v
            int min_dist = D[current_idx][v];

            // Check all incoming edges to see if we can find a shorter path via w
            for (const auto& edge : graph[v]) {
                int w = edge.from;
                if (D[current_idx][w] != INF) {
                    min_dist = min(min_dist, D[current_idx][w] + edge.weight);
                }
            }

            // Write result to the NEXT buffer. 
            // Since only this thread writes to D[next_idx][start_v ... end_v-1], 
            // data race is structurally impossible.
            D[next_idx][v] = min_dist;
        }

        // Wait for all other threads to finish this iteration.
        sync_barrier.arrive_and_wait();
    }
}

int main() {
    const int V = 10; // Number of vertices
    const int E = 20; // Number of edges
    const int num_threads = 4;
    const int start_vertex = 0;

    cout << "Initializing Graph Generation...\n";
    auto graph = generateGraph(V, E);

    // Print the graph to console for visual verification
    printGraph(graph);

    // Double buffer for distances: D[2][V]
    vector<vector<int>> D(2, vector<int>(V, INF));

    // Initialization: distance to start vertex is 0
    D[0][start_vertex] = 0;

    cout << "Starting parallel Shortest Path algorithm...\n";
    cout << "Working with " << num_threads << " threads.\n";

    // Synchronize threads
    barrier sync_barrier(num_threads);

    vector<thread> threads;

    // Calculate chunk sizes for threads
    int chunk_size = V / num_threads;
    int remainder = V % num_threads;
    int current_start = 0;

    // auto start_time = chrono::high_resolution_clock::now();

    // Spawn threads
    for (int i = 0; i < num_threads; ++i) {
        int current_end = current_start + chunk_size + (i < remainder ? 1 : 0);

        threads.emplace_back(worker, i, current_start, current_end, V,
            cref(graph), ref(D), ref(sync_barrier));

        current_start = current_end;
    }

    // Wait for all threads to complete
    for (auto& t : threads) {
        t.join();
    }

    // Determine which buffer holds the final result
    int final_idx = V % 2;

    // Output Statistics and Results
    cout << "\nSTATISTICS:\n";
    cout << "Total Vertices (V) : " << V << "\n";
    cout << "Total Edges (E)    : " << E << "\n";
    cout << "Worker Threads     : " << num_threads << "\n";
    cout << "Target Iterations  : " << V << " (Formula N = |V|)\n";
    cout << "Total Barrier Syncs: " << V << "\n\n";

    cout << "Minimal Distances from Vertex " << start_vertex << "\n";
    for (int i = 0; i < V; ++i) {
        cout << "Vertex " << setw(2) << i << " : ";
        if (D[final_idx][i] == INF) {
            cout << "UNREACHABLE\n";
        }
        else {
            cout << D[final_idx][i] << "\n";
        }
    }

    return 0;
}