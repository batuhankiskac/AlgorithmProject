*Interpretation.* The measurements match the analysis.

- *TS iteration.* The slope is close to 1, as predicted by $Theta(n k)$ with fixed $k$. Without the candidate list it would be 2.
- *Split.* The unlimited Split has slope about 1. This is the $O(n L)$ bound with $L approx 6.5$ independent of $n$, not the worst case $O(n^2)$.
- *Clarke–Wright.* The slope is slightly above 2, consistent with $O(n^2 log n)$: over $n in [25, 800]$, the extra $log n$ factor adds about 0.2 to the fitted slope.
- *GA generation.* Its slope lies between the two terms identified above. The fleet-limited Split costs $O(K n L)$ with $K approx n\/6.5$, so it grows quadratically. The local search, which dominates at small $n$, grows roughly linearly. As $n$ grows the quadratic term takes over, and the local slope between $n = 400$ and $800$ is about 1.75.

@tab:delta shows the other half of the story. A delta evaluation costs a constant 0.2–0.4 µs, while a full re-evaluation grows linearly. The speed-up rises from about 15× at $n = 50$ to over 100× at $n = 800$, exactly the predicted factor $Theta(n)$. In pure Python, this is the difference between about 1,300 and about 20 TS iterations per second at $n = 100$.
