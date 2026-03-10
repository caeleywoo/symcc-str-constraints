(set-logic ALL)
(set-option :incremental true)
(set-option :produce-models true)


(declare-fun |stdin0| () String)
(declare-fun |fread0| () Int)

(assert (>= fread0 0))
(assert (not (>= fread0 59)))
(assert (= fread0 (str.len (str.substr stdin0 0 fread0))))
(assert (= fread0 (str.len (str.substr stdin0 0 58))))
(assert (not (>= fread0 60)))
(assert (not (>= (str.to_code (str.substr (str.substr stdin0 0 fread0) 0 1)) 256)))
(assert (not (= (str.to_code (str.substr (str.substr stdin0 0 fread0) 0 1)) 0)))

(check-sat)
