(set-logic ALL)
(set-option :incremental true)
(set-option :produce-models true)


(declare-fun |stdin0| () String)
(declare-fun |fread0| () Int)

(assert (>= fread0 0))
(assert (not (>= fread0 72)))
(assert (= fread0 (str.len (str.substr stdin0 0 fread0))))
(assert (= fread0 (str.len (str.substr stdin0 0 71))))
(assert (not (>= fread0 73)))
(assert (not (>= (str.to_code (str.substr stdin0 70 (+ (- 70) fread0))) 256)))
(assert (not (= (str.to_code (str.substr stdin0 70 (+ (- 70) fread0))) 10)))
(assert (not (str.contains (str.substr stdin0 0 (str.indexof (str.++ (str.substr stdin0 0 fread0) "\u{0}") "\u{0}" 0)) "#")))

(check-sat)
