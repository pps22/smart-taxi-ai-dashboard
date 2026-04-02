from __future__ import annotations

from dataclasses import dataclass, field
from heapq import heappop, heappush
from typing import Dict, List, Optional, Set, Tuple

Position = Tuple[int, int]


@dataclass
class Passenger:
    pickup: Position
    destination: Position
    picked_up: bool = False
    delivered: bool = False


class GridWorld:
    """A richer grid world for an explainable taxi agent."""

    ACTIONS: Dict[str, Tuple[int, int]] = {
        "North": (-1, 0),
        "South": (1, 0),
        "East": (0, 1),
        "West": (0, -1),
    }

    def __init__(
        self,
        size: int = 5,
        start: Position = (0, 0),
        blocked: Optional[Set[Position]] = None,
        traffic_costs: Optional[Dict[Position, int]] = None,
        passenger: Optional[Passenger] = None,
        name: str = "Scenario",
    ):
        if size < 5:
            raise ValueError("Grid must be at least 5x5.")
        self.size = size
        self.start = start
        self.blocked = set(blocked or set())
        self.traffic_costs = dict(traffic_costs or {})
        self.passenger = passenger or Passenger((1, 2), (4, 4))
        self.name = name

        important_cells = {self.start, self.passenger.pickup, self.passenger.destination}
        if important_cells & self.blocked:
            raise ValueError("Start, pickup, and destination must not be blocked.")

    def in_bounds(self, position: Position) -> bool:
        x, y = position
        return 0 <= x < self.size and 0 <= y < self.size

    def is_blocked(self, position: Position) -> bool:
        return position in self.blocked

    def cell_cost(self, position: Position) -> int:
        """Base movement cost = 1, with extra cost for traffic-heavy cells."""
        return 1 + self.traffic_costs.get(position, 0)

    def neighbors(self, position: Position) -> List[Tuple[str, Position]]:
        result = []
        for action, (dx, dy) in self.ACTIONS.items():
            nxt = (position[0] + dx, position[1] + dy)
            if self.in_bounds(nxt) and not self.is_blocked(nxt):
                result.append((action, nxt))
        return result


@dataclass
class Performance:
    score: int = 0
    steps: int = 0
    replans: int = 0
    invalid_attempts: int = 0
    goal_achieved: bool = False
    path_cost: int = 0
    action_log: List[str] = field(default_factory=list)

    MOVE_PENALTY: int = -1
    INVALID_MOVE_PENALTY: int = -10
    REPLAN_PENALTY: int = -1
    PICKUP_REWARD: int = 10
    DROPOFF_REWARD: int = 100

    def register_move(self, action: str, destination: Position, cost: int) -> None:
        self.steps += 1
        self.path_cost += cost
        # -1 base move penalty, then extra penalty for traffic-heavy cells.
        self.score += self.MOVE_PENALTY - (cost - 1)
        self.action_log.append(f"MOVE {action} -> {destination} (cost {cost})")

    def register_invalid(self, attempted: Position) -> None:
        self.invalid_attempts += 1
        self.score += self.INVALID_MOVE_PENALTY
        self.action_log.append(f"INVALID -> {attempted}")

    def register_replan(self, reason: str) -> None:
        self.replans += 1
        self.score += self.REPLAN_PENALTY
        self.action_log.append(f"REPLAN: {reason}")

    def register_pickup(self, location: Position) -> None:
        self.score += self.PICKUP_REWARD
        self.action_log.append(f"PICKUP at {location}")

    def register_dropoff(self, location: Position) -> None:
        self.score += self.DROPOFF_REWARD
        self.goal_achieved = True
        self.action_log.append(f"DROPOFF at {location}")


@dataclass(order=True)
class SearchNode:
    priority: int
    position: Position = field(compare=False)
    g_cost: int = field(compare=False)
    path: List[str] = field(compare=False, default_factory=list)


class TaxiAgent:
    def __init__(self, environment: GridWorld):
        self.env = environment
        self.location = environment.start
        self.has_passenger = False
        self.explanations: List[str] = []
        self.last_planned_path: List[str] = []
        self.last_target: Optional[Position] = None

    def perceive(self) -> Dict[str, object]:
        passenger_goal = self.env.passenger.destination if self.has_passenger else self.env.passenger.pickup
        return {
            "taxi_location": self.location,
            "passenger_location": self.env.passenger.pickup,
            "passenger_destination": self.env.passenger.destination,
            "carrying_passenger": self.has_passenger,
            "blocked_roads": sorted(self.env.blocked),
            "traffic_costs": dict(sorted(self.env.traffic_costs.items())),
            "current_goal": passenger_goal,
            "legal_actions": [action for action, _ in self.env.neighbors(self.location)],
        }

    @staticmethod
    def heuristic(a: Position, b: Position) -> int:
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def plan_path(self, goal: Position) -> Optional[List[str]]:
        """A* search with weighted traffic costs."""
        frontier: List[SearchNode] = []
        heappush(frontier, SearchNode(self.heuristic(self.location, goal), self.location, 0, []))
        best_cost: Dict[Position, int] = {self.location: 0}

        while frontier:
            node = heappop(frontier)
            if node.position == goal:
                self.last_planned_path = node.path
                self.last_target = goal
                return node.path

            for action, nxt in self.env.neighbors(node.position):
                new_cost = node.g_cost + self.env.cell_cost(nxt)
                if nxt not in best_cost or new_cost < best_cost[nxt]:
                    best_cost[nxt] = new_cost
                    priority = new_cost + self.heuristic(nxt, goal)
                    heappush(frontier, SearchNode(priority, nxt, new_cost, node.path + [action]))
        return None

    def choose_next_action(self, goal: Position) -> Optional[str]:
        path = self.plan_path(goal)
        if not path:
            self.explanations.append(
                f"No action selected because there is no safe path from {self.location} to {goal}."
            )
            return None

        next_action = path[0]
        predicted = self.preview_move(next_action)
        remaining_steps = len(path)
        cost_of_next = self.env.cell_cost(predicted) if predicted else None

        explanation = (
            f"I chose {next_action} from {self.location} because A* found the lowest-cost route "
            f"to {goal}. The next cell {predicted} is legal, avoids blocked roads, "
            f"has immediate travel cost {cost_of_next}, and leaves {remaining_steps - 1} moves after this one."
        )
        self.explanations.append(explanation)
        return next_action

    def preview_move(self, action: str) -> Optional[Position]:
        if action not in self.env.ACTIONS:
            return None
        dx, dy = self.env.ACTIONS[action]
        return (self.location[0] + dx, self.location[1] + dy)

    def apply_action(self, action: str, performance: Performance) -> bool:
        nxt = self.preview_move(action)
        if nxt is None or not self.env.in_bounds(nxt) or self.env.is_blocked(nxt):
            performance.register_invalid(nxt if nxt is not None else (-1, -1))
            return False

        cost = self.env.cell_cost(nxt)
        self.location = nxt
        performance.register_move(action, nxt, cost)
        return True

    def try_pickup(self, performance: Performance) -> bool:
        passenger = self.env.passenger
        if self.location == passenger.pickup and not passenger.picked_up:
            passenger.picked_up = True
            self.has_passenger = True
            performance.register_pickup(self.location)
            self.explanations.append(
                f"I picked up the passenger at {self.location} because I reached the requested pickup point."
            )
            return True
        return False

    def try_dropoff(self, performance: Performance) -> bool:
        passenger = self.env.passenger
        if self.location == passenger.destination and self.has_passenger:
            passenger.delivered = True
            self.has_passenger = False
            performance.register_dropoff(self.location)
            self.explanations.append(
                f"I dropped off the passenger at {self.location} because this matches the destination."
            )
            return True
        return False

    def mission_target(self) -> Position:
        return self.env.passenger.destination if self.has_passenger else self.env.passenger.pickup

    def run(self, max_iterations: int = 200, verbose: bool = True) -> Dict[str, object]:
        performance = Performance()
        iteration = 0

        if verbose:
            print(f"\n=== {self.env.name} ===")
            print("Initial percepts:", self.perceive())

        while iteration < max_iterations:
            iteration += 1
            target = self.mission_target()

            if not self.has_passenger and self.try_pickup(performance):
                if verbose:
                    print(f"Passenger picked up at {self.location}")
                continue

            if self.try_dropoff(performance):
                if verbose:
                    print(f"Passenger dropped off at {self.location}")
                break

            action = self.choose_next_action(target)
            if action is None:
                performance.register_replan("Search failed: no safe path exists.")
                break

            if verbose:
                print(f"At {self.location}, target {target}, action {action}")
                print("Why?", self.explanations[-1])

            success = self.apply_action(action, performance)
            if not success:
                performance.register_replan("Chosen move became invalid during execution.")
                if verbose:
                    print("Execution failure: invalid move encountered.")
                continue

        return {
            "scenario": self.env.name,
            "score": performance.score,
            "steps": performance.steps,
            "path_cost": performance.path_cost,
            "replans": performance.replans,
            "invalid_attempts": performance.invalid_attempts,
            "goal_achieved": performance.goal_achieved,
            "final_location": self.location,
            "passenger_delivered": self.env.passenger.delivered,
            "percepts_at_end": self.perceive(),
            "explanations": self.explanations,
            "action_log": performance.action_log,
        }


def print_report(result: Dict[str, object]) -> None:
    print("\nScenario Results")
    print(f"Scenario: {result['scenario']}")
    print(f"Total Score: {result['score']}")
    print(f"Steps Taken: {result['steps']}")
    print(f"Weighted Path Cost: {result['path_cost']}")
    print(f"Replans: {result['replans']}")
    print(f"Invalid Attempts: {result['invalid_attempts']}")
    print(f"Goal Achieved: {result['goal_achieved']}")
    print(f"Passenger Delivered: {result['passenger_delivered']}")
    print(f"Final Location: {result['final_location']}")
    print("Sample Justifications:")
    for sentence in result["explanations"][:4]:
        print("-", sentence)


if __name__ == "__main__":
    scenarios = [
        GridWorld(
            size=5,
            start=(0, 0),
            blocked={(2, 2), (3, 1)},
            traffic_costs={(1, 1): 2, (1, 2): 1, (2, 1): 2},
            passenger=Passenger((1, 2), (4, 4)),
            name="Scenario 1 - Standard Pickup and Delivery",
        ),
        GridWorld(
            size=6,
            start=(0, 0),
            blocked={(1, 1), (1, 2), (2, 2), (4, 3)},
            traffic_costs={(2, 0): 3, (3, 0): 2, (4, 0): 1},
            passenger=Passenger((3, 0), (5, 4)),
            name="Scenario 2 - Traffic-Aware Route Choice",
        ),
        GridWorld(
            size=6,
            start=(5, 0),
            blocked={(1, 3), (2, 3), (3, 3), (4, 3), (3, 1)},
            traffic_costs={(5, 1): 2, (4, 1): 2, (2, 2): 3, (0, 4): 2},
            passenger=Passenger((2, 4), (0, 5)),
            name="Scenario 3 - Long Detour Around Blocked Corridor",
        ),
    ]

    results = []
    for env in scenarios:
        agent = TaxiAgent(env)
        result = agent.run(verbose=True)
        print_report(result)
        results.append(result)

    print("\n=== Summary Table ===")
    for result in results:
        print(
            f"{result['scenario']}: score={result['score']}, steps={result['steps']}, "
            f"path_cost={result['path_cost']}, goal={result['goal_achieved']}"
        )
