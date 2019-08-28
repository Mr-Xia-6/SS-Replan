from __future__ import print_function

import cProfile
import pstats

#from examples.discrete_belief.run import MAX_COST
from examples.discrete_belief.run import clip_cost
from pddlstream.algorithms.constraints import PlanConstraints, OrderedSkeleton
from pddlstream.algorithms.focused import solve_focused
from pddlstream.algorithms.algorithm import reset_globals
from pddlstream.algorithms.downward import set_cost_scale

from pddlstream.language.constants import print_solution
from pddlstream.language.stream import StreamInfo, PartialInputs
from pddlstream.language.function import FunctionInfo
from pddlstream.language.object import SharedOptValue
from pddlstream.utils import INF

from pybullet_tools.utils import LockRenderer, WorldSaver, wait_for_user, VideoSaver, wait_for_duration
from src.command import Wait, iterate_commands, Trajectory, DEFAULT_TIME_STEP
from src.stream import detect_cost_fn, compute_detect_cost, COST_SCALE
from src.replan import INTERNAL_ACTIONS

# TODO: use the same objects for poses and configs
from src.utils import RelPose

COST_BOUND = 1000.0
# TODO: multiple cost bounds

################################################################################

def opt_detect_cost_fn(obj_name, rp_dist, obs, rp_sample):
    # TODO: prune these surfaces if the cost is already too high
    if isinstance(rp_sample, RelPose):
        # This shouldn't be needed if eager=True
        return detect_cost_fn(obj_name, rp_dist, obs, rp_sample)
    prob = rp_dist.surface_prob(rp_dist.surface_name)
    #print(rp_dist.surface_name, prob)
    cost = clip_cost(compute_detect_cost(prob))
    print('{}) Opt Detect Prob: {:.3f} | Opt Detect Cost: {:.3f} | Type: {}'.format(
        rp_dist.surface_name, prob, cost, rp_sample.__class__.__name__))
    return cost

def opt_move_base_test(bq1, bq2, aq): #, fluents=[]):
    if isinstance(bq1, SharedOptValue) or isinstance(bq2, SharedOptValue):
        return True
    #if isinstance(UniqueOptValue, bq1) and (aq1 == bq2):
    #    pass
    return bq1 != bq2

def opt_move_arm_gen_test(bq, aq1, aq2): #, fluents=[]):
    if isinstance(aq1, SharedOptValue) or isinstance(aq2, SharedOptValue):
        return True
    return aq1 != aq2

def get_stream_info():
    opt_gen_fn = PartialInputs(unique=False)
    stream_info = {
        'test-gripper': StreamInfo(p_success=0, eager=True),
        'test-door': StreamInfo(p_success=0, eager=True),
        'test-near-pose': StreamInfo(p_success=0, eager=True),
        'test-near-joint': StreamInfo(p_success=0, eager=True),

        # TODO: need to be careful about conditional effects
        'compute-pose-kin': StreamInfo(opt_gen_fn=PartialInputs(unique=True),
                                       p_success=0.5, eager=True),
        # 'compute-angle-kin': StreamInfo(p_success=0.5, eager=True),
        'sample-pose': StreamInfo(opt_gen_fn=opt_gen_fn),
        'sample-nearby-pose': StreamInfo(opt_gen_fn=opt_gen_fn),
        'sample-grasp': StreamInfo(opt_gen_fn=opt_gen_fn),

        'compute-detect': StreamInfo(opt_gen_fn=opt_gen_fn, p_success=1e-4),

        'plan-pick': StreamInfo(opt_gen_fn=opt_gen_fn, overhead=1e1),
        'fixed-plan-pick': StreamInfo(opt_gen_fn=opt_gen_fn, overhead=1e1),
        # TODO: can't defer this because collision streams depend on it
        'plan-pull': StreamInfo(opt_gen_fn=opt_gen_fn, overhead=1e1, defer=False),
        'fixed-plan-pull': StreamInfo(opt_gen_fn=opt_gen_fn, overhead=1e1),

        'plan-press': StreamInfo(opt_gen_fn=opt_gen_fn, overhead=1e1, defer=False),
        'fixed-plan-press': StreamInfo(opt_gen_fn=opt_gen_fn, overhead=1e1),

        # 'plan-calibrate-motion': StreamInfo(opt_gen_fn=opt_gen_fn),
        'plan-base-motion': StreamInfo(opt_gen_fn=PartialInputs(test=opt_move_base_test),
                                       overhead=1e3, defer=True),
        'plan-arm-motion': StreamInfo(opt_gen_fn=PartialInputs(test=opt_move_arm_gen_test),
                                      overhead=1e2, defer=True),
        # 'plan-gripper-motion': StreamInfo(opt_gen_fn=opt_gen_fn),

        'test-cfree-worldpose': StreamInfo(p_success=1e-3, negate=True,
                                           verbose=False),
        'test-cfree-worldpose-worldpose': StreamInfo(p_success=1e-3, negate=True,
                                                     verbose=False),
        'test-cfree-pose-pose': StreamInfo(p_success=1e-3, negate=True,
                                           verbose=False),
        'test-cfree-bconf-pose': StreamInfo(p_success=1e-3, negate=True,
                                            verbose=False),
        'test-cfree-approach-pose': StreamInfo(p_success=1e-2, negate=True,
                                               verbose=False),
        'test-cfree-angle-angle': StreamInfo(p_success=1e-2, negate=True,
                                             verbose=False),
        'test-cfree-traj-pose': StreamInfo(p_success=1e-1, negate=True,
                                           verbose=False),

        'test-ofree-ray-pose': StreamInfo(p_success=1e-3, negate=True,
                                          verbose=False),
        'test-ofree-ray-grasp': StreamInfo(p_success=1e-3, negate=True,
                                           verbose=False),

        'DetectCost': FunctionInfo(opt_detect_cost_fn, eager=True),
        # 'Distance': FunctionInfo(p_success=0.99, opt_fn=lambda bq1, bq2: BASE_CONSTANT),
        # 'MoveCost': FunctionInfo(lambda t: BASE_CONSTANT),
    }
    return stream_info

################################################################################

def create_ordered_skeleton(skeleton):
    if skeleton is None:
        return None
    #skeletons = [skeleton]
    #return skeletons
    orders = set()
    #orders = linear_order(skeleton)
    last_step = None
    for step, (name, args) in enumerate(skeleton):
        if last_step is not None:
            orders.add((last_step, step))
        if name not in INTERNAL_ACTIONS:
            last_step = step
    return [OrderedSkeleton(skeleton, orders)]

def solve_pddlstream(belief, problem, args, skeleton=None, replan_actions=set(), max_time=INF, max_cost=INF):
    set_cost_scale(COST_SCALE)
    reset_globals()
    stream_info = get_stream_info()
    #print(set(stream_map) - set(stream_info))
    skeletons = create_ordered_skeleton(skeleton)
    max_cost = min(max_cost, COST_BOUND)
    print('Max cost: {:.3f} | Max runtime: {:.3f}'.format(max_cost, max_time))
    constraints = PlanConstraints(skeletons=skeletons, max_cost=max_cost, exact=True)

    success_cost = 0 if args.anytime else INF
    planner = 'ff-astar' if args.anytime else 'ff-wastar2'
    search_sample_ratio = 0.5 # 0.5
    max_planner_time = 10

    pr = cProfile.Profile()
    pr.enable()
    saver = WorldSaver()
    sim_state = belief.sample_state()
    sim_state.assign()
    wait_for_duration(0.1)
    with LockRenderer(lock=not args.visualize):
        # TODO: option to only consider costs during local optimization
        # effort_weight = 0 if args.anytime else 1
        effort_weight = 1e-3 if args.anytime else 1
        #effort_weight = 0
        solution = solve_focused(problem, constraints=constraints, stream_info=stream_info,
                                 replan_actions=replan_actions,
                                 initial_complexity=5,
                                 planner=planner, max_planner_time=max_planner_time,
                                 unit_costs=args.unit, success_cost=success_cost,
                                 max_time=max_time, verbose=True, debug=False,
                                 unit_efforts=True, effort_weight=effort_weight, max_effort=INF,
                                 # bind=True, max_skeletons=None,
                                 search_sample_ratio=search_sample_ratio)
        saver.restore()

    # print([(s.cost, s.time) for s in SOLUTIONS])
    # print(SOLUTIONS)
    print_solution(solution)
    pr.disable()
    pstats.Stats(pr).sort_stats('tottime').print_stats(25)  # cumtime | tottime
    return solution

################################################################################

def extract_plan_prefix(plan, replan_actions=set()):
    if plan is None:
        return None
    prefix = []
    for action in plan:
        name, args = action
        prefix.append(action)
        if name in replan_actions:
            break
    return prefix

def combine_commands(commands):
    combined_commands = []
    for command in commands:
        if not combined_commands:
            combined_commands.append(command)
            continue
        prev_command = combined_commands[-1]
        if isinstance(prev_command, Trajectory) and isinstance(command, Trajectory) and \
                (prev_command.joints == command.joints):
            prev_command.path = (prev_command.path + command.path)
        else:
            combined_commands.append(command)
    return combined_commands

def commands_from_plan(world, plan):
    if plan is None:
        return None
    # TODO: propagate the state
    commands = []
    for action, params in plan:
        # TODO: break if the action is a StreamAction
        if action in ['move_base', 'move_arm', 'move_gripper', 'pick', 'pull', 'press']:
            commands.extend(params[-1].commands)
        elif action == 'detect':
            commands.append(params[-1])
        elif action == 'place':
            commands.extend(params[-1].reverse().commands)
        elif action in ['cook', 'calibrate']:
            # TODO: calibrate action that uses fixed_base_suppressor
            #steps = int(math.ceil(2.0 / DEFAULT_TIME_STEP))
            steps = 0
            commands.append(Wait(world, steps=steps))
        else:
            raise NotImplementedError(action)
    return commands
    #return combine_commands(commands)

################################################################################

VIDEO_TEMPLATE = '{}.mp4'

def simulate_plan(state, commands, args, time_step=DEFAULT_TIME_STEP):
    wait_for_user()
    if commands is None:
        return
    time_step = None if args.teleport else time_step
    if args.record:
        video_path = VIDEO_TEMPLATE.format(args.problem)
        with VideoSaver(video_path):
            iterate_commands(state, commands, time_step=time_step)
        print('Saved', video_path)
    else:
        iterate_commands(state, commands, time_step=time_step)
