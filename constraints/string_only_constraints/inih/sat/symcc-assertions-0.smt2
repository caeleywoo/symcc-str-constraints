(set-logic ALL)
(set-option :incremental true)
(set-option :produce-models true)


(declare-fun |stdin0| () String)
(declare-fun |fgets0| () String)
(declare-fun |fgets1| () String)

(assert (not (str.contains (str.substr stdin0 0 199) "\u{a}")))

(check-sat)
