import numpy as np

from pybullet_tools.utils import get_point, convex_hull, Point, add_segments, convex_centroid, add_text, spaced_colors, \
    multiply, point_from_pose, get_pose, invert, link_from_name, grow_polygon, GREEN
from src.database import load_pull_base_poses, get_surface_reference_pose, load_placements, \
    load_place_base_poses, load_forward_placements
from src.utils import ALL_JOINTS, ALL_SURFACES, GRASP_TYPES, get_grasps, surface_from_name


def visualize_base_confs(world, name, base_confs, floor_z=0.005, **kwargs):
    handles = []
    if not base_confs:
        return handles
    z = get_point(world.floor)[2] + floor_z
    # for x, y in base_points:
    #    handles.extend(draw_point(Point(x, y, z), color=color))
    vertices = grow_polygon(base_confs, radius=0.05)
    points = [Point(x, y, z) for x, y, in vertices]
    handles.extend(add_segments(points, closed=True, **kwargs))
    cx, cy = convex_centroid(vertices)
    centroid = [cx, cy, z]
    # draw_point(centroid, color=color)
    handles.append(add_text(name, position=centroid, **kwargs))
    return handles

def get_forward_reachability(world):
    for surface_name in ALL_SURFACES:
        surface = surface_from_name(surface_name)

        for grasp_type, color in zip(GRASP_TYPES):
            object_points = []
            for surface_from_object in load_placements(world, surface_name, grasp_types=[grasp_type]):
                # object_points.append(point_from_pose(multiply(surface_pose, surface_from_object)))
                object_points.append(point_from_pose(surface_from_object))
            if not object_points:
                continue


def add_markers(world, placements=True, forward_place=True, pull_bases=True, inverse_place=False):
    handles = []
    if placements:
        for surface_name in ALL_SURFACES:
            surface = surface_from_name(surface_name)
            surface_link = link_from_name(world.kitchen, surface.link)
            for grasp_type, color in zip(GRASP_TYPES, spaced_colors(len(GRASP_TYPES))):
                object_points = list(map(point_from_pose, load_placements(world, surface_name,
                                                                          grasp_types=[grasp_type])))
                if object_points:
                    #for object_point in object_points:
                    #    handles.extend(draw_point(object_point, color=color))
                    _, _, z = np.average(object_points, axis=0)
                    object_points = [Point(x, y, z) for x, y, in grow_polygon(object_points, radius=0.05)]
                    handles.extend(add_segments(object_points, color=color, closed=True,
                                                parent=world.kitchen, parent_link=surface_link))
                base_points = []
                for surface_from_object in load_placements(world, surface_name, grasp_types=[grasp_type]):
                    object_points.append(point_from_pose(surface_from_object))



    if forward_place:
        object_points = list(map(point_from_pose, load_forward_placements(world)))
        object_points = [Point(x, y, z=0.) for x, y, in grow_polygon(object_points, radius=0.0)]
        handles.extend(add_segments(object_points, color=GREEN, closed=True,
                                    parent=world.robot, parent_link=world.base_link))

    if pull_bases:
        for joint_name, color in zip(ALL_JOINTS, spaced_colors(len(ALL_JOINTS))):
            base_confs = list(load_pull_base_poses(world, joint_name))
            handles.extend(visualize_base_confs(world, joint_name, base_confs, color=color))

    if inverse_place:
        # TODO: could make relative as well
        for name in world.movable:
            body = world.get_body(name)
            pose = get_pose(body)
            surface_name = world.get_supporting(name)
            if surface_name is None:
                continue
            for grasp_type, color in zip(GRASP_TYPES, spaced_colors(len(GRASP_TYPES))):
                base_confs = []
                for grasp in get_grasps(world, name, grasp_types=[grasp_type]):
                    tool_pose = multiply(pose, invert(grasp.grasp_pose))
                    base_confs.extend(load_place_base_poses(world, tool_pose, surface_name, grasp_type))
                handles.extend(visualize_base_confs(world, grasp_type, base_confs, color=color))

    return handles