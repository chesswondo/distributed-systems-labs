#include <iostream>
#include <vector>
#include <thread>
#include <mutex>
#include <semaphore>
#include <random>
#include <chrono>
#include <array>
#include <memory>
#include <string>

#if defined(_WIN32) || defined(_WIN64)
#include <Windows.h>
inline void set_color(int color) {
    SetConsoleTextAttribute(GetStdHandle(STD_OUTPUT_HANDLE), color);
}
#else
inline void set_color(int) {}
#endif

using namespace std::chrono_literals;

// Philosopher states
enum class State { THINK = 0, WAIT = 1, EAT = 2, STOP = 3 };
constexpr int N = 5;

// Synchronization strategy
class IDiningStrategy {
public:
    virtual ~IDiningStrategy() = default;
    virtual void get_forks(int id) = 0;
    virtual void put_forks(int id) = 0;
};

// Single semaphore strategy
class WaiterStrategy : public IDiningStrategy {
    // N-1 philosophers max
    std::counting_semaphore<N - 1> waiter{ N - 1 };
    std::array<std::mutex, N> forks;

public:
    void get_forks(int id) override {
        waiter.acquire();
        int left = id;
        int right = (id + 1) % N;

        forks[left].lock();
        forks[right].lock();
    }

    void put_forks(int id) override {
        int left = id;
        int right = (id + 1) % N;

        forks[right].unlock();
        forks[left].unlock();

        waiter.release(); // Release a place for other
    }
};

// Tanenbaum algorithm
class TanenbaumStrategy : public IDiningStrategy {
    enum class PState { THINKING, HUNGRY, EATING };
    std::mutex state_mutex;
    std::array<PState, N> states{};
    std::vector<std::unique_ptr<std::binary_semaphore>> sems;

    int left(int i) { return (i + N - 1) % N; }
    int right(int i) { return (i + 1) % N; }

    // Check: can i-th philosopher sart eating?
    void test(int i) {
        if (states[i] == PState::HUNGRY &&
            states[left(i)] != PState::EATING &&
            states[right(i)] != PState::EATING) {

            states[i] = PState::EATING;
            sems[i]->release();
        }
    }

public:
    TanenbaumStrategy() {
        for (int i = 0; i < N; ++i) {
            // Blocked by default
            sems.push_back(std::make_unique<std::binary_semaphore>(0));
        }
    }

    void get_forks(int id) override {
        {
            std::lock_guard<std::mutex> lock(state_mutex);
            states[id] = PState::HUNGRY;
            test(id); // Try to eat
        }
        sems[id]->acquire(); // Block if fail
    }

    void put_forks(int id) override {
        std::lock_guard<std::mutex> lock(state_mutex);
        states[id] = PState::THINKING;
        // Check neighbors
        test(left(id));
        test(right(id));
    }
};

// Simulation logic
class DiningSimulation {
    IDiningStrategy& strategy;
    std::array<State, N> philosopher_states{};
    std::mutex output_mutex;
    std::atomic<bool> keep_running{ true };

    void report(int id, State s) {
        std::lock_guard<std::mutex> lock(output_mutex);
        philosopher_states[id] = s;

        int eats = 0;
        for (int i = 0; i < N; ++i) {
            State current_state = philosopher_states[i];

            // Colors: THINK=LightBlue(9), WAIT=Yellow(14), EAT=Green(10), STOP=Red(12)
            int colors[] = { 9, 14, 10, 12 };
            set_color(colors[static_cast<int>(current_state)]);

            const char chars[] = { 'T', 'W', 'E', 'S' };
            std::cout << chars[static_cast<int>(current_state)] << " ";

            if (current_state == State::EAT) eats++;
        }
        set_color(8);
        std::cout << " Total eaters: " << eats << "\n";
        set_color(7);
    }

    void philosopher_routine(int id) {
        // Thread-local generator
        thread_local std::default_random_engine reng(std::random_device{}());
        thread_local std::uniform_int_distribution<> distr(500, 2500);

        while (keep_running) {
            // Think
            report(id, State::THINK);
            std::this_thread::sleep_for(std::chrono::milliseconds(distr(reng)));

            // Try to get forks
            report(id, State::WAIT);
            strategy.get_forks(id);

            // Eat
            report(id, State::EAT);
            std::this_thread::sleep_for(std::chrono::milliseconds(distr(reng)));

            // Put forks
            report(id, State::STOP);
            strategy.put_forks(id);
        }
    }

public:
    DiningSimulation(IDiningStrategy& strat) : strategy(strat) {
        for (auto& s : philosopher_states) s = State::THINK;
    }

    void run() {
        std::vector<std::jthread> threads;
        for (int i = 0; i < N; ++i) {
            threads.emplace_back(&DiningSimulation::philosopher_routine, this, i);
        }

        std::cout << "Press Enter to stop the simulation...\n";
        std::cin.get();
        keep_running = false;
    }
};

int main(int argc, char* argv[]) {
    // Select the algorithm
    bool use_tanenbaum = true;

    if (use_tanenbaum) {
        std::cout << "Starting Tanenbaum's Algorithm (Mutex + 5 Semaphores)\n";
        TanenbaumStrategy strat;
        DiningSimulation sim(strat);
        sim.run();
    }
    else {
        std::cout << "Starting Waiter Algorithm (1 Counting Semaphore)\n";
        WaiterStrategy strat;
        DiningSimulation sim(strat);
        sim.run();
    }

    return 0;
}