// CMP 3005 Term Project report. Build: python report/build.py
#set document(title: "Drones, Deadlines and NP-Hardness", author: "MediDrone team")
#set page(paper: "a4", margin: (x: 2.1cm, y: 2.2cm), numbering: "1",
  header: context { if counter(page).get().first() > 1 [
    #set text(8pt, fill: luma(110))
    CMP 3005 – Analysis of Algorithms · Term Project #h(1fr) Metaheuristics for a Capacitated Medical Delivery Network
  ] })
#set text(font: ("New Computer Modern", "Libertinus Serif"), size: 10.5pt, lang: "en")
#set par(justify: true, leading: 0.62em, spacing: 0.95em)
#set heading(numbering: "1.1")
#show heading.where(level: 1): it => { v(0.6em); text(13.5pt, it); v(0.25em) }
#show heading.where(level: 2): it => { v(0.3em); text(11.5pt, it); v(0.1em) }
#show figure.caption: set text(9pt)
#show table: set text(8.6pt)
#set table(stroke: (x, y) => if y == 0 { (bottom: 0.7pt) } else { none }, inset: (x: 5pt, y: 3.2pt))
#set math.equation(numbering: "(1)")
#show raw: set text(8.5pt)

// ---------- title ----------
#align(center)[
  #text(9.5pt, fill: luma(90))[CMP 3005 – Analysis of Algorithms · Fall 2026–2027 · Term Project]
  #v(0.3em)
  #text(17pt, weight: "bold")[Drones, Deadlines and NP-Hardness]
  #v(0.1em)
  #text(12.5pt)[Metaheuristics for a Capacitated Medical Delivery Network]
  #v(0.5em)
  #text(10pt)[Team: #include "sections/team.typ"]
  #v(0.1em)
  #text(9pt, fill: luma(90))[Instructor: Dr. Günet Eroğlu · Submitted 13 December 2026 · Code: #link("https://github.com/batuhankiskac/AlgorithmProject")[github.com/batuhankiskac/AlgorithmProject]]
]
#v(0.6em)
#block(inset: (x: 1.2cm))[
  #set text(9.5pt)
  *Abstract.* #include "sections/abstract.typ"
]
#v(0.4em)

#include "sections/intro.typ"
#include "sections/theory.typ"
#include "sections/methods.typ"
#include "sections/complexity.typ"
#include "sections/experiments.typ"
#include "sections/discussion.typ"

#bibliography("refs.bib", title: "References", style: "ieee")

#pagebreak()
#set heading(numbering: "A.1")
#counter(heading).update(0)
#include "sections/appendix.typ"
