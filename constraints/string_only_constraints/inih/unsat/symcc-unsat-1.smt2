(set-logic ALL)
(set-option :incremental true)
(set-option :produce-models true)


(declare-fun |stdin0| () String)
(declare-fun |fgets0| () String)
(declare-fun |fgets1| () String)

(assert (str.contains (str.substr stdin0 0 199) "\u{a}"))
(assert (= (str.substr stdin0 0 199) (str.++ fgets0 "\u{a}" fgets1)))
(assert (not (str.contains fgets0 "\u{0}")))

(check-sat)
