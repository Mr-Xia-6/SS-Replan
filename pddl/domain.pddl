(define (domain nvidia-tamp)
  (:requirements :strips :equality)
  (:constants @world @gripper @stove
              @open @closed
              @rest_aq @calibrate_aq
              @open_gq @closed_gq)
  (:predicates
    (Stackable ?o ?r)
    (Stove ?r)
    (Type ?t ?b)
    (NoisyBase)
    (Movable ?o)
    (Counter ?o ?p)
    (Graspable ?o)

    (Pick ?o ?p ?g ?bq ?aq ?at)
    (Pull ?j ?q1 ?q2 ?bq ?aq1 ?aq2 ?at)
    (BaseMotion ?bq1 ?bq2 ?aq ?bt)
    (ArmMotion ?bq ?aq1 ?aq2 ?at)
    (GripperMotion ?gq1 ?gq2 ?gt)
    (CalibrateMotion ?bq ?aq ?at)
    (Detect ?c ?o ?p ?r)

    (Grasp ?o ?g)
    (BTraj ?bt)
    (ATraj ?at)
    (BConf ?bq)
    (AConf ?bq ?aq)
    (GConf ?gq)
    (Angle ?j ?a)
    (Ray ?r)

    (CFreeRelPoseRelPose ?o1 ?rp1 ?o2 ?rp2 ?s)
    (CFreeApproachPose ?o1 ?p1 ?g ?o2 ?p2)
    (CFreeTrajPose ?t ?o2 ?p2)
    (OFreeRayPose ?r ?o ?p)
    (OFreeRayGrasp ?r ?bq ?aq ?o ?g)

    (HandEmpty)
    (AtBConf ?bq)
    (AtAConf ?aq)
    (AtGConf ?gq)
    (AtRelPose ?o1 ?rp ?o2)
    (AtWorldPose ?o ?p)
    (AtGrasp ?o ?g)
    (AtAngle ?j ?q)

    (CanMoveBase)
    (CanMoveArm)
    (CanMoveGripper)
    (Cooked ?o)
    (Calibrated)
    (Detected ?o)

    (OpenGripper)
    (OpenGConf ?gq)

    (Status ?s)
    (DoorStatus ?j ?s)
    (AngleWithin ?j ?a ?s)

    (On ?o1 ?o2)
    (Holding ?o)
    (Accessible ?o ?p)
    (UnsafeRelPose ?o ?rp ?s)
    (UnsafeApproach ?o ?p ?g)
    (UnsafeATraj ?at)
    (UnsafeBTraj ?bt)
    (OccludedRay ?r)

    (RelPose ?o1 ?rp ?o2)
    (WorldPose ?o ?p)
    (PoseKin ?o1 ?p1 ?rp ?o2 ?p2)
    (Connected ?o ?j)
    (AngleKin ?o ?p ?j ?a)
    (AdmitsGrasp ?o1 ?g ?o2)
  )
  (:functions
    (Distance ?bq1 ?bq2)
    (MoveBaseCost)
    (MoveArmCost)
    (MoveGripperCost)
    (PickCost)
    (PlaceCost)
    (PullCost)
    (CookCost)
  )

  (:action move_base
    ;:parameters (?bq1 ?bq2 ?aq ?bt)
    ;:precondition (and (BaseMotion ?bq1 ?bq2 ?aq ?bt)
    ;                   (AtBConf ?bq1) (AtAConf ?aq)
    :parameters (?bq1 ?bq2 ?bt)
    :precondition (and (BaseMotion ?bq1 ?bq2 @rest_aq ?bt)
                       (AtBConf ?bq1) (AtAConf @rest_aq)
                       (Calibrated) (CanMoveBase))
    :effect (and (AtBConf ?bq2)
                 (CanMoveArm)
                 (not (AtBConf ?bq1))
                 (not (CanMoveBase))
                 (not (Calibrated))
                 ;(when (NoisyBase) (not (Calibrated)))
                 ;(increase (total-cost) (Distance ?bq1 ?bq2)))
                 (increase (total-cost) (MoveBaseCost)))
  )
  (:action move_arm
    :parameters (?bq ?aq1 ?aq2 ?at)
    :precondition (and (ArmMotion ?bq ?aq1 ?aq2 ?at)
                       (AtBConf ?bq) (AtAConf ?aq1)
                       ; (Calibrated) ; TODO: require calibration?
                       (CanMoveArm))
    :effect (and (AtAConf ?aq2)
                 (not (AtAConf ?aq1)) (not (CanMoveArm))
                 (increase (total-cost) (MoveArmCost)))
  )
  (:action move_gripper
    :parameters (?gq1 ?gq2 ?gt)
    :precondition (and (GripperMotion ?gq1 ?gq2 ?gt)
                       (AtGConf ?gq1)) ; (CanMoveGripper))
    :effect (and (AtGConf ?gq2)
                 (not (AtGConf ?gq1)) (not (CanMoveGripper))
                 (increase (total-cost) (MoveGripperCost)))
  )

  (:action calibrate
    ;:parameters (?bq ?aq ?at)
    ;:precondition (and (CalibrateMotion ?bq ?aq ?at)
    :parameters (?bq)
    :precondition (and (AConf ?bq @calibrate_aq)
                       (AtBConf ?bq) (AtAConf @calibrate_aq)
                       (not (Calibrated))
                       ; TODO: visibility constraints
                   )
    :effect (and (Calibrated) (CanMoveArm)
                 ; (not (AtBConf ?bq)) ; Could make this be a new pose ?bq2
                 (increase (total-cost) (CalibrateCost)))
  )
  (:action pick
    :parameters (?o1 ?p1 ?g ?rp ?o2 ?p2 ?bq ?aq ?at)
    :precondition (and (Pick ?o1 ?p1 ?g ?bq ?aq ?at) (PoseKin ?o1 ?p1 ?rp ?o2 ?p2)
                       (AtRelPose ?o1 ?rp ?o2) (AtWorldPose ?o1 ?p1) (HandEmpty)
                       (AtBConf ?bq) (Calibrated)
                       (AtAConf ?aq) (OpenGripper)
                       (Accessible ?o2 ?p2) (AdmitsGrasp ?o1 ?g ?o2)
                       (not (UnsafeApproach ?o1 ?p1 ?g))
                       (not (UnsafeATraj ?at))
                       ; TODO: detect precondition
                  )
    :effect (and (AtGrasp ?o1 ?g)
                 (CanMoveBase) (CanMoveArm)
                 (Holding ?o1) (not (On ?o1 ?o2))
                 (not (AtRelPose ?o1 ?rp ?o2)) (not (AtWorldPose ?o1 ?p1))
                 (not (HandEmpty)) (not (Detected ?o1))
                 (increase (total-cost) (PickCost)))
  )
  (:action place
    :parameters (?o1 ?p1 ?g ?rp ?o2 ?p2 ?bq ?aq ?at)
    :precondition (and (Pick ?o1 ?p1 ?g ?bq ?aq ?at) (PoseKin ?o1 ?p1 ?rp ?o2 ?p2)
                       (AtGrasp ?o1 ?g) (AtWorldPose ?o2 ?p2)
                       (AtBConf ?bq) (Calibrated)
                       (AtAConf ?aq) ; (AtGConf @closed_gq)
                       (Accessible ?o2 ?p2) (AdmitsGrasp ?o1 ?g ?o2)
                       (not (UnsafeRelPose ?o1 ?rp ?o2))
                       (not (UnsafeApproach ?o1 ?p1 ?g))
                       (not (UnsafeATraj ?at))
                  )
    :effect (and (AtRelPose ?o1 ?rp ?o2) (AtWorldPose ?o1 ?p1) (HandEmpty)
                 (On ?o1 ?o2) (not (Holding ?o1))
                 (CanMoveBase) (CanMoveArm)
                 (not (AtGrasp ?o1 ?g))
                 (increase (total-cost) (PlaceCost)))
  )
  (:action pull
    :parameters (?j ?a1 ?a2 ?o ?p1 ?p2 ?bq ?aq1 ?aq2 ?at)
    :precondition (and (Pull ?j ?a1 ?a2 ?bq ?aq1 ?aq2 ?at)
                       (AngleKin ?o ?p1 ?j ?a1) (AngleKin ?o ?p2 ?j ?a2)
                       (AtAngle ?j ?a1) (HandEmpty)
                       (AtWorldPose ?o ?p1)
                       (AtBConf ?bq) (Calibrated)
                       (AtAConf ?aq1) (OpenGripper)
                       ; TODO: ensure the final conf is safe
                       (not (UnsafeATraj ?at))
                  )
    :effect (and (AtAngle ?j ?a2) (AtWorldPose ?o ?p2) (AtAConf ?aq2)
                 (CanMoveBase) (CanMoveArm)
                 (not (AtAngle ?j ?a1)) (not (AtWorldPose ?o ?p1)) (not (AtAConf ?aq1))
                 (forall (?o3 ?p3 ?rp3) (when (and (PoseKin ?o3 ?p3 ?rp3 ?o ?p1)
                                                   (AtRelPose ?o3 ?rp3 ?o))
                                              (not (AtWorldPose ?o3 ?p3))))
                 (forall (?o4 ?p4 ?rp4) (when (and (PoseKin ?o4 ?p4 ?rp4 ?o ?p2)
                                                   (AtRelPose ?o4 ?rp4 ?o))
                                              (AtWorldPose ?o4 ?p4)))
                 (increase (total-cost) (PullCost)))
  )

  (:action detect
    :parameters (?c ?o ?p ?r)
    :precondition (and (Detect ?c ?o ?p ?r)
                       (AtWorldPose ?o ?p)
                       (not (OccludedRay ?r))
                  )
    :effect (Detected ?o)
  )


  ;(:action cook
  ;  :parameters (?r)
  ;  :precondition (Type ?r @stove)
  ;  :effect (and (forall (?o) (when (On ?o ?r) (Cooked ?o)))
  ;               (increase (total-cost) (CookCost)))
  ;)

  ;(:derived (On ?o1 ?o2)
  ;  (exists (?rp) (and (RelPose ?o1 ?rp ?o2)
  ;                     (AtRelPose ?o1 ?rp ?o2)))
  ;)
  ;(:derived (Holding ?o)
  ;  (exists (?g) (and (Grasp ?o ?g)
  ;                    (AtGrasp ?o ?g)))
  ;)
  (:derived (OpenGripper)
    ;(AtGConf @open_gq)
    (exists (?gq) (and (OpenGConf ?gq)
                       (AtGConf ?gq)))
  )

  (:derived (DoorStatus ?j ?s)
    (exists (?a) (and (AngleWithin ?j ?a ?s)
                      (AtAngle ?j ?a)))
  )
  (:derived (Accessible ?o ?p) (or
    (Counter ?o ?p)
    (exists (?j ?a) (and (AngleKin ?o ?p ?j ?a) (AngleWithin ?j ?a @open)
                         (AtAngle ?j ?a))))
  )
  ;(:derived (AdmitsGrasp ?o ?g ?o2) ; Static fact
  ;  (exists (?gty) (and (IsGraspType ?o ?g ?gty) (AdmitsGraspType ?o2 ?gty)))
  ;)

  ; https://github.mit.edu/mtoussai/KOMO-stream/blob/master/03-Caelans-pddlstreamExample/retired/domain.pddl
  ;(:derived (AtWorldPose ?o1 ?p1) (or
  ;  (and (RelPose ?o1 ?p1 @world)
  ;       (AtRelPose ?o1 ?p1 @world))
  ;  (exists (?rp ?o2 ?p2) (and (PoseKin ?o1 ?p1 ?rp ?o2 ?p2)
  ;          (AtWorldPose ?o2 ?p2) (AtRelPose ?o1 ?rp ?o2)))
  ;  (exists (?j ?a) (and (AngleKin ?o1 ?p1 ?j ?a)
  ;          (AtAngle ?j ?a))) ; TODO: could compose arbitrary chains
  ;))

  (:derived (UnsafeRelPose ?o1 ?rp1 ?s) (and (RelPose ?o1 ?rp1 ?s)
    (exists (?o2 ?rp2) (and (RelPose ?o2 ?rp2 ?s) (Graspable ?o2) (not (= ?o1 ?o2))
                            (not (CFreeRelPoseRelPose ?o1 ?rp1 ?o2 ?rp2 ?s))
                            (AtRelPose ?o2 ?rp2 ?s)))
  ))
  (:derived (UnsafeApproach ?o1 ?p1 ?g) (and (WorldPose ?o1 ?p1) (Grasp ?o1 ?g)
    (exists (?o2 ?p2) (and (WorldPose ?o2 ?p2) (Movable ?o2) (not (= ?o1 ?o2))
                           (not (CFreeApproachPose ?o1 ?p1 ?g ?o2 ?p2))
                           (AtWorldPose ?o2 ?p2)))
  ))
  (:derived (UnsafeATraj ?at) (and (ATraj ?at)
    (exists (?o2 ?p2) (and (WorldPose ?o2 ?p2) (Movable ?o2)
                           (not (CFreeTrajPose ?at ?o2 ?p2))
                           (AtWorldPose ?o2 ?p2)))
  ))

  (:derived (OccludedRay ?r) (and (Ray ?r) (or
    (exists (?o ?p) (and (WorldPose ?o ?p) (Movable ?o)
                         (not (OFreeRayPose ?r ?o ?p))
                         (AtWorldPose ?o ?p)))
    (exists (?bq ?aq ?o ?g) (and (AConf ?bq ?aq) (Grasp ?o ?g)
                            (not (OFreeRayGrasp ?r ?bq ?aq ?o ?g))
                            (AtBConf ?bq) (AtAConf ?aq) (AtGrasp ?o ?g)))
  )))
)