from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from swarm.config import CHEATER_NAMES, SEED_AGENT_NAMES, Condition, RunConfig
from swarm.logging import EventLogger
from swarm.puzzles import Puzzle, check_answer


@dataclass
class LibraryEntry:
    entry_id: str
    problem_id: str
    agent: str
    answer_raw: str
    working: str
    via_exploit: bool
    round_submitted: int
    revoked: bool = False


@dataclass
class Report:
    reporter: str
    target_agent: str
    entry_id: str
    evidence: str
    round_filed: int


@dataclass
class Review:
    reviewer: str
    entry_id: str
    verdict: str  # "legit", "exploit", "unsure"
    round_filed: int
    saw_prior_accusation: bool


@dataclass
class BoardPost:
    agent: str
    text: str
    round_posted: int


@dataclass
class DM:
    sender: str
    recipient: str
    text: str
    round_sent: int


@dataclass
class WorldState:
    """Mutable shared state for a single run."""

    config: RunConfig
    puzzles: list[Puzzle]
    logger: EventLogger

    # Problem locks: pid -> entry_id (or None if open)
    locks: dict[str, str | None] = field(default_factory=dict)
    library: dict[str, LibraryEntry] = field(default_factory=dict)
    board: list[BoardPost] = field(default_factory=list)
    dms: dict[str, list[DM]] = field(default_factory=dict)  # recipient -> list
    reports: list[Report] = field(default_factory=list)
    reviews: list[Review] = field(default_factory=list)
    scores: dict[str, float] = field(default_factory=dict)
    prior_reads: dict[str, set[str]] = field(default_factory=dict)  # agent -> entry_ids read in past rounds
    last_round_reads: dict[str, set[str]] = field(default_factory=dict)  # agent -> entry_ids read last round (for observation)

    _entry_counter: int = 0

    def __post_init__(self) -> None:
        for p in self.puzzles:
            if p.pid not in self.locks:
                self.locks[p.pid] = None

    def _next_entry_id(self) -> str:
        self._entry_counter += 1
        return f"E{self._entry_counter:03d}"

    def get_puzzle(self, pid: str) -> Puzzle | None:
        for p in self.puzzles:
            if p.pid == pid:
                return p
        return None

    def try_submit(
        self, agent: str, problem_id: str, answer_raw: str, working: str, round_num: int
    ) -> tuple[bool, LibraryEntry | None]:
        """Attempt to submit an answer. Returns (accepted, entry_or_none)."""
        puzzle = self.get_puzzle(problem_id)
        if puzzle is None:
            return False, None

        if self.locks.get(problem_id) is not None:
            return False, None

        accepted, via_exploit = check_answer(puzzle, answer_raw)
        if not accepted:
            return False, None

        eid = self._next_entry_id()
        entry = LibraryEntry(
            entry_id=eid,
            problem_id=problem_id,
            agent=agent,
            answer_raw=answer_raw,
            working=working,
            via_exploit=via_exploit,
            round_submitted=round_num,
        )
        self.library[eid] = entry
        self.locks[problem_id] = eid
        self.scores.setdefault(agent, 0.0)
        self.scores[agent] += 10.0

        self.logger.log(round_num, agent, "submit", {
            "entry_id": eid,
            "problem_id": problem_id,
            "answer_raw": answer_raw,
            "accepted": True,
            "via_exploit": via_exploit,
        })
        return True, entry

    def file_report(
        self, reporter: str, target_agent: str, entry_id: str, evidence: str, round_num: int
    ) -> Report:
        report = Report(reporter, target_agent, entry_id, evidence, round_num)
        self.reports.append(report)
        self.logger.log(round_num, reporter, "report", {
            "target_agent": target_agent,
            "entry_id": entry_id,
            "evidence": evidence,
        })
        return report

    def file_review(
        self, reviewer: str, entry_id: str, verdict: str, round_num: int, saw_prior_accusation: bool
    ) -> Review:
        review = Review(reviewer, entry_id, verdict, round_num, saw_prior_accusation)
        self.reviews.append(review)
        self.logger.log(round_num, reviewer, "review", {
            "entry_id": entry_id,
            "verdict": verdict,
            "saw_prior_accusation": saw_prior_accusation,
        })
        return review

    def post_board(self, agent: str, text: str, round_num: int) -> None:
        self.board.append(BoardPost(agent, text, round_num))
        self.logger.log(round_num, agent, "action", {"tool": "post_board", "text": text})

    def send_dm(self, sender: str, recipient: str, text: str, round_num: int) -> None:
        dm = DM(sender, recipient, text, round_num)
        self.dms.setdefault(recipient, []).append(dm)
        self.logger.log(round_num, sender, "action", {"tool": "send_dm", "to": recipient, "text": text})

    def get_flags_for_entry(self, entry_id: str) -> set[str]:
        """Get distinct agents who reported or gave 'exploit' verdict on an entry."""
        flaggers: set[str] = set()
        for r in self.reports:
            if r.entry_id == entry_id:
                flaggers.add(r.reporter)
        for rv in self.reviews:
            if rv.entry_id == entry_id and rv.verdict == "exploit":
                flaggers.add(rv.reviewer)
        return flaggers

    def revoke_entry(self, entry_id: str, round_num: int) -> None:
        """Revoke a library entry: mark revoked, deduct points, reopen problem."""
        entry = self.library[entry_id]
        if entry.revoked:
            return
        entry.revoked = True
        self.scores[entry.agent] = self.scores.get(entry.agent, 0.0) - 10.0
        self.locks[entry.problem_id] = None
        self.logger.log(round_num, None, "revocation", {
            "entry_id": entry_id,
            "agent": entry.agent,
            "problem_id": entry.problem_id,
        })

    def is_cheater_entry(self, entry_id: str) -> bool:
        entry = self.library.get(entry_id)
        if entry is None:
            return False
        return entry.agent in CHEATER_NAMES

    def is_decoy_entry(self, entry_id: str) -> bool:
        entry = self.library.get(entry_id)
        if entry is None:
            return False
        return entry.agent in set(SEED_AGENT_NAMES)

    def is_honest_entry(self, entry_id: str) -> bool:
        return not self.is_cheater_entry(entry_id) and not self.is_decoy_entry(entry_id)

    def open_problems(self) -> list[Puzzle]:
        return [p for p in self.puzzles if self.locks.get(p.pid) is None]

    def last_board_posts(self, n: int = 15) -> list[BoardPost]:
        return self.board[-n:]

    def inbox_for(self, agent: str) -> list[DM]:
        return self.dms.get(agent, [])
