(set-logic ALL)
(set-option :incremental true)
(set-option :produce-models true)


(declare-fun |stdin0| () String)
(declare-fun |fgets0| () String)
(declare-fun |fgets1| () String)

(assert (str.contains (str.substr stdin0 0 199) "\u{a}"))
(assert (= (str.substr stdin0 0 199) (str.++ fgets0 "\u{a}" fgets1)))
(assert (not (str.contains fgets0 "\u{0}")))
(assert (not (>= (str.len fgets0) 200)))
(assert (not (>= (str.to_code (str.substr (str.++ fgets0 "\u{0}") 0 1)) 256)))
(assert (not (>= (str.to_code (str.substr (str.++ fgets0 "\u{0}") 1 1)) 256)))
(assert (not (= (str.to_code (str.substr (str.++ fgets0 "\u{0}") 0 1)) 239)))
(assert (not (>= (str.to_code (str.substr (str.++ fgets0 "\u{0}") 2 1)) 256)))
(assert (not (>= (str.len fgets0) 1)))

(check-sat)
