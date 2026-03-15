(set-logic ALL)
(set-option :incremental true)
(set-option :produce-models true)


(declare-fun |stdin0| () String)
(declare-fun |fread0| () Int)

(assert (>= fread0 0))
(assert (not (>= fread0 20)))
(assert (= fread0 (str.len (str.substr stdin0 0 fread0))))
(assert (= fread0 (str.len (str.substr stdin0 0 19))))
(assert (not (>= fread0 21)))
(assert (not (= fread0 19)))

(check-sat)
