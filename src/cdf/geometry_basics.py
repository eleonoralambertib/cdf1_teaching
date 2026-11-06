"""
Geometry basics -- reusable Rhino.Geometry functions for Grasshopper.

Adding a new function with Copilot
-----------------------------------
1. Open this file and select this chat model, then ask Copilot something like:
   "Add a function here, all in Rhino geometry, that builds a <your shape/idea>.
   Follow the same style as create_cone / create_fractal_tree (defaults for
   optional inputs, a docstring listing params, return a Rhino.Geometry object)."
2. Once the function is added, ask Copilot:
   "Give me the Python code to use this function in a Grasshopper GHPython 3
   component, importing it from computational_design_and_fabrication."
3. Copy the snippet Copilot gives you into a GHPython component, wire up the
   inputs as sliders/panels, and set the output variable (e.g. `a`).
"""

import math
import Rhino.Geometry as rg  # type: ignore[reportMissingImports]
import random

def create_cone(base_point=None, height=10.0, radius=5.0, cap_bottom=True):
    """
    Build a cone as a Brep.

    base_point : Rhino.Geometry.Point3d -- center of the cone's base circle
    height     : float -- cone height along the base plane's normal (Z by default)
    radius     : float -- base circle radius
    cap_bottom : bool  -- whether to cap the base circle (closed vs open cone)

    Returns a Rhino.Geometry.Brep.
    """
    if base_point is None:
        base_point = rg.Point3d(0, 0, 0)

    plane = rg.Plane(base_point, rg.Vector3d.ZAxis)
    cone = rg.Cone(plane, height, radius)
    return cone.ToBrep(cap_bottom)

def create_sphere(center_point=None, radius=5.0):
    """
    Build a sphere as a Brep.

    center_point : Rhino.Geometry.Point3d -- center of the sphere
    radius       : float -- sphere radius

    Returns a Rhino.Geometry.Brep.
    """
    if center_point is None:
        center_point = rg.Point3d(0, 0, 0)

    sphere = rg.Sphere(center_point, radius)
    return sphere.ToBrep()

def create_random_spheres_in_cube(
    sphere_count=20,
    corner_point=None,
    cube_size=10.0,
    width=None,
    depth=None,
    height=None,
    min_radius=0.3,
    max_radius=0.8,
    clearance=0.01,
    seed=None,
    max_attempts=1000,
):
    """
    Randomly place non-intersecting spheres inside an imaginary box.

    sphere_count : int -- number of spheres; accepts integer-valued numeric inputs
    corner_point : Rhino.Geometry.Point3d -- minimum corner of the box
    cube_size    : float -- fallback length for each side when dimensions are omitted
    width        : float -- box size along X; defaults to cube_size
    depth        : float -- box size along Y; defaults to cube_size
    height       : float -- box size along Z; defaults to cube_size
    min_radius   : float -- minimum sphere radius
    max_radius   : float -- maximum sphere radius
    clearance    : float -- minimum gap between spheres and from cube walls
    seed         : int -- optional random seed for repeatable results
    max_attempts : int -- placement attempts allowed for each sphere

    Returns a list of Rhino.Geometry.Brep spheres. If the requested number
    cannot be placed, returns the spheres placed before placement attempts fail.
    """
    try:
        integer_sphere_count = int(sphere_count)
        integer_max_attempts = int(max_attempts)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError("sphere_count and max_attempts must be integers.") from error
    if integer_sphere_count != sphere_count or integer_max_attempts != max_attempts:
        raise ValueError("sphere_count and max_attempts must be whole numbers.")
    sphere_count = integer_sphere_count
    max_attempts = integer_max_attempts

    if corner_point is None:
        corner_point = rg.Point3d(0, 0, 0)
    width = cube_size if width is None else width
    depth = cube_size if depth is None else depth
    height = cube_size if height is None else height
    if sphere_count < 0:
        raise ValueError("sphere_count must not be negative.")
    if width <= 0 or depth <= 0 or height <= 0:
        raise ValueError("width, depth, and height must be positive.")
    if min_radius <= 0 or max_radius < min_radius:
        raise ValueError("Radii must be positive and max_radius >= min_radius.")
    if clearance <= 0:
        raise ValueError("clearance must be positive to keep spheres off each other and the walls.")
    if max_attempts <= 0:
        raise ValueError("max_attempts must be positive.")
    if 2.0 * (max_radius + clearance) > min(width, depth, height):
        raise ValueError("The largest sphere does not fit inside the box with the requested clearance.")

    rng = random.Random(seed)
    placed = []

    for _ in range(sphere_count):
        for _ in range(max_attempts):
            radius = rng.uniform(min_radius, max_radius)
            inset = radius + clearance
            point = rg.Point3d(
                rng.uniform(corner_point.X + inset, corner_point.X + width - inset),
                rng.uniform(corner_point.Y + inset, corner_point.Y + depth - inset),
                rng.uniform(corner_point.Z + inset, corner_point.Z + height - inset),
            )

            if all(
                point.DistanceTo(other_center) > radius + other_radius + clearance
                for other_center, other_radius in placed
            ):
                placed.append((point, radius))
                break
        else:
            break

    return [rg.Sphere(point, radius).ToBrep() for point, radius in placed]

def boolean_difference(brep_a, brep_b, brep_c=None):
    """
    Subtract one or two Breps from a first Brep.

    brep_a : Rhino.Geometry.Brep -- the first Brep
    brep_b : Rhino.Geometry.Brep -- a Brep to subtract from the first
    brep_c : Rhino.Geometry.Brep -- an optional second Brep to subtract

    Returns a list of Rhino.Geometry.Brep resulting from the difference.
    """
    if brep_a is None or brep_b is None:
        raise ValueError("Both brep_a and brep_b must be provided.")

    if brep_c is None:
        result = rg.Brep.CreateBooleanDifference(brep_a, brep_b, 0.001)
    else:
        result = rg.Brep.CreateBooleanDifference([brep_a], [brep_b, brep_c], 0.001)
    return result


def copy_brep_along_z(brep, distance, copy_count):
    """
    Create copies of a Brep, each offset in the +Z direction.

    brep : Rhino.Geometry.Brep -- the Brep to copy
    distance : float -- the Z spacing between consecutive copies
    copy_count : int -- the number of copies to create

    Returns a list of Rhino.Geometry.Brep copies; copy i is moved by distance * (i + 1).
    """
    if brep is None:
        raise ValueError("brep must be provided.")
    if copy_count < 0:
        raise ValueError("copy_count must not be negative.")

    copies = []
    for i in range(1, int(copy_count) + 1):
        copy = brep.DuplicateBrep()
        copy.Transform(rg.Transform.Translation(rg.Vector3d(0, 0, distance * i)))
        copies.append(copy)
    return copies

def copy_box_along_z_decreasing_height(box, distance, copy_count, height_decrement):
    """
    Create copies of a box along +X, reducing each copy's height along Z.

    box : Rhino.Geometry.Brep -- the box to copy
    distance : float -- the X offset between consecutive copies
    copy_count : int -- the number of copies to create
    height_decrement : float -- amount subtracted from the height for each copy

    Returns a list of Rhino.Geometry.Brep copies; copy i is moved along X by
    distance * i and has height reduced by height_decrement * i.
    """
    if box is None:
        raise ValueError("box must be provided.")
    if copy_count < 0:
        raise ValueError("copy_count must not be negative.")
    if height_decrement <= 0:
        raise ValueError("height_decrement must be positive.")

    copy_count = int(copy_count)
    if copy_count == 0:
        return []

    bounds = box.GetBoundingBox(True)
    if not bounds.IsValid:
        raise ValueError("box must have a valid bounding box.")

    height = bounds.Max.Z - bounds.Min.Z
    if height <= 0 or height_decrement * copy_count >= height:
        raise ValueError("height_decrement would make a copy's height non-positive.")

    scale_plane = rg.Plane(
        rg.Point3d(bounds.Min.X, bounds.Min.Y, bounds.Min.Z),
        rg.Vector3d.ZAxis,
    )
    copies = []
    for i in range(1, copy_count + 1):
        copy = box.DuplicateBrep()
        height_scale = (height - height_decrement * i) / height
        copy.Transform(rg.Transform.Scale(scale_plane, 1.0, 1.0, height_scale))
        copy.Transform(rg.Transform.Translation(rg.Vector3d(distance * i, 0, 0)))
        copies.append(copy)
    return copies

def copy_brep_along_vector(brep, vector, copy_count):
    """
    Create copies of a Brep, each offset along a specified vector.

    brep : Rhino.Geometry.Brep -- the Brep to copy
    vector : Rhino.Geometry.Vector3d -- the direction and distance for each copy
    copy_count : int -- the number of copies to create

    Returns a list of Rhino.Geometry.Brep copies; copy i is moved by vector * (i + 1).
    """
    if brep is None:
        raise ValueError("brep must be provided.")
    if copy_count < 0:
        raise ValueError("copy_count must not be negative.")

    copies = []
    for i in range(1, int(copy_count) + 1):
        copy = brep.DuplicateBrep()
        translation_vector = rg.Vector3d(vector)
        translation_vector *= i
        copy.Transform(rg.Transform.Translation(translation_vector))
        copies.append(copy)
    return copies

def copy_curve_along_z(curve, distance, copy_count):
    """
    Create copies of a curve, each offset in the +Z direction.

    curve : Rhino.Geometry.Curve -- the curve to copy
    distance : float -- the Z spacing between consecutive copies
    copy_count : int -- the number of copies to create

    Returns a list of Rhino.Geometry.Curve copies; copy i is moved by distance * (i + 1).
    """
    if curve is None:
        raise ValueError("curve must be provided.")
    if copy_count < 0:
        raise ValueError("copy_count must not be negative.")

    copies = []
    for i in range(1, int(copy_count) + 1):
        copy = curve.DuplicateCurve()
        copy.Transform(rg.Transform.Translation(rg.Vector3d(0, 0, distance * i)))
        copies.append(copy)
    return copies

def copy_curve_along_vector(curve, vector, copy_count):
    """
    Create copies of a curve, each offset along a specified vector.

    curve : Rhino.Geometry.Curve -- the curve to copy
    vector : Rhino.Geometry.Vector3d -- the direction and distance for each copy
    copy_count : int -- the number of copies to create

    Returns a list of Rhino.Geometry.Curve copies; copy i is moved by vector * (i + 1).
    """
    if curve is None:
        raise ValueError("curve must be provided.")
    if copy_count < 0:
        raise ValueError("copy_count must not be negative.")

    copies = []
    for i in range(1, int(copy_count) + 1):
        copy = curve.DuplicateCurve()
        translation_vector = rg.Vector3d(vector)
        translation_vector *= i
        copy.Transform(rg.Transform.Translation(translation_vector))
        copies.append(copy)
    return copies

def create_fractal_tree(base_point=None, height=10.0, radius=1.0, levels=3, branch_angle=30.0):
    """
    Build a simple fractal tree as a Brep.

    base_point : Rhino.Geometry.Point3d -- the starting point of the tree
    height     : float -- the height of the initial trunk
    radius     : float -- the radius of the trunk
    levels     : int -- the number of branching levels
    branch_angle : float -- the angle (in degrees) between branches

    Returns a list of Rhino.Geometry.Brep representing the tree structure.
    """
    if base_point is None:
        base_point = rg.Point3d(0, 0, 0)

    def add_branch(point, height, radius, level):
        if level == 0:
            return []

        # Create trunk
        trunk = create_cone(point, height, radius)
        branches = [trunk]

        # Calculate new branch points
        top_point = rg.Point3d(point.X, point.Y, point.Z + height)
        angle_rad = math.radians(branch_angle)

        # Left branch
        left_vector = rg.Vector3d(-math.sin(angle_rad) * height / 2, 0, math.cos(angle_rad) * height / 2)
        left_branch_point = top_point + left_vector
        branches += add_branch(left_branch_point, height / 2, radius / 2, level - 1)

        # Right branch
        right_vector = rg.Vector3d(math.sin(angle_rad) * height / 2, 0, math.cos(angle_rad) * height / 2)
        right_branch_point = top_point + right_vector
        branches += add_branch(right_branch_point, height / 2, radius / 2, level - 1)

        return branches

    return add_branch(base_point, height, radius, levels)

def create_cylinder(base_point=None, height=10.0, radius=5.0, cap_top=True, cap_bottom=True):
    """
    Build a cylinder as a Brep.

    base_point : Rhino.Geometry.Point3d -- center of the cylinder's base circle
    height     : float -- cylinder height along the base plane's normal (Z by default)
    radius     : float -- base circle radius
    cap_top    : bool  -- whether to cap the top circle (closed vs open cylinder)
    cap_bottom : bool  -- whether to cap the bottom circle (closed vs open cylinder)

    Returns a Rhino.Geometry.Brep.
    """
    if base_point is None:
        base_point = rg.Point3d(0, 0, 0)

    plane = rg.Plane(base_point, rg.Vector3d.ZAxis)
    base_circle = rg.Circle(plane, radius)
    cylinder = rg.Cylinder(base_circle, height)
    return cylinder.ToBrep(cap_bottom, cap_top)

def create_circle(center_point=None, radius=5.0):
    """
    Build a circle as a closed NURBS curve in the world XY plane.

    center_point : Rhino.Geometry.Point3d -- center of the circle (default is origin)
    radius       : float -- circle radius

    Returns a Rhino.Geometry.NurbsCurve.
    """
    if center_point is None:
        center_point = rg.Point3d(0, 0, 0)
    if radius <= 0:
        raise ValueError("radius must be positive.")

    plane = rg.Plane(center_point, rg.Vector3d.ZAxis)
    return rg.Circle(plane, radius).ToNurbsCurve()

def create_square_curve(center_point=None, side_length=10.0):
    """
    Build a square as a closed NURBS curve in the world XY plane.

    center_point : Rhino.Geometry.Point3d -- center of the square (default is origin)
    side_length  : float -- length of each side

    Returns a closed Rhino.Geometry.NurbsCurve.
    """
    if center_point is None:
        center_point = rg.Point3d(0, 0, 0)
    if side_length <= 0:
        raise ValueError("side_length must be positive.")

    half_side = side_length / 2.0
    points = [
        rg.Point3d(center_point.X - half_side, center_point.Y - half_side, center_point.Z),
        rg.Point3d(center_point.X + half_side, center_point.Y - half_side, center_point.Z),
        rg.Point3d(center_point.X + half_side, center_point.Y + half_side, center_point.Z),
        rg.Point3d(center_point.X - half_side, center_point.Y + half_side, center_point.Z),
        rg.Point3d(center_point.X - half_side, center_point.Y - half_side, center_point.Z),
    ]
    return rg.Polyline(points).ToNurbsCurve()

def create_box(corner_point=None, width=10.0, depth=10.0, height=10.0):
    """
    Build a box as a Brep.

    corner_point : Rhino.Geometry.Point3d -- the corner of the box (default is origin)
    width        : float -- width of the box along the X-axis
    depth        : float -- depth of the box along the Y-axis
    height       : float -- height of the box along the Z-axis

    Returns a Rhino.Geometry.Brep.
    """
    if corner_point is None:
        corner_point = rg.Point3d(0, 0, 0)

    plane = rg.Plane(corner_point, rg.Vector3d.ZAxis)
    box = rg.Box(
        plane,
        rg.Interval(0, width),
        rg.Interval(0, depth),
        rg.Interval(0, height),
    )
    return box.ToBrep()

def create_loft_solid(profile_a, profile_b, tolerance=0.01):
    """
    Create a solid by lofting between two closed profile curves.

    profile_a  : Rhino.Geometry.Curve -- first closed section curve
    profile_b  : Rhino.Geometry.Curve -- second closed section curve
    tolerance  : float -- tolerance used to cap the loft's planar ends

    Returns a closed Rhino.Geometry.Brep.
    """
    if profile_a is None or profile_b is None:
        raise ValueError("Both profile_a and profile_b must be provided.")
    if not profile_a.IsClosed or not profile_b.IsClosed:
        raise ValueError("Both profile curves must be closed.")
    if tolerance <= 0:
        raise ValueError("tolerance must be positive.")

    lofts = rg.Brep.CreateFromLoft(
        [profile_a, profile_b],
        rg.Point3d.Unset,
        rg.Point3d.Unset,
        rg.LoftType.Normal,
        False,
    )
    if lofts is None or len(lofts) == 0:
        raise RuntimeError("The loft operation did not produce a Brep.")

    solid = lofts[0].CapPlanarHoles(tolerance)
    if solid is None or not solid.IsSolid:
        raise RuntimeError(
            "The loft was created, but its ends could not be capped into a solid. "
            "Check that both profiles are planar and compatible."
        )
    return solid

def sweep_square_along_helix(center_point=None, turns=3.0, radius=5.0, axis_length=10.0, side_length=1.0, cap_ends=True, tolerance=0.01):
    """
    Sweep a square cross-section along a vertical helical curve.

    center_point : Rhino.Geometry.Point3d -- center of the helix axis at its base
    turns        : float -- number of complete turns
    radius       : float -- radius of the helix
    axis_length  : float -- vertical distance from the first to last turn
    side_length  : float -- side length of the square cross-section
    cap_ends     : bool -- whether to cap the two ends of the sweep
    tolerance    : float -- sweep tolerance

    Returns a Rhino.Geometry.Brep.
    """
    if center_point is None:
        center_point = rg.Point3d(0, 0, 0)
    if turns <= 0 or radius <= 0 or axis_length <= 0 or side_length <= 0 or tolerance <= 0:
        raise ValueError("turns, radius, axis_length, side_length, and tolerance must be positive.")

    point_count = max(24, int(math.ceil(turns * 24)) + 1)
    rail_points = []
    for i in range(point_count):
        fraction = i / float(point_count - 1)
        angle = 2.0 * math.pi * turns * fraction
        rail_points.append(
            rg.Point3d(
                center_point.X + radius * math.cos(angle),
                center_point.Y + radius * math.sin(angle),
                center_point.Z + axis_length * fraction,
            )
        )
    rail = rg.Curve.CreateInterpolatedCurve(rail_points, 3)
    if rail is None:
        raise RuntimeError("Could not create the helical rail curve.")

    tangent = rg.Vector3d(0, 2.0 * math.pi * turns * radius, axis_length)
    tangent.Unitize()
    radial = rg.Vector3d(1, 0, 0)
    transverse = rg.Vector3d.CrossProduct(tangent, radial)
    transverse.Unitize()

    half_side = side_length / 2.0
    start = rail_points[0]
    profile_points = [
        start - radial * half_side - transverse * half_side,
        start + radial * half_side - transverse * half_side,
        start + radial * half_side + transverse * half_side,
        start - radial * half_side + transverse * half_side,
        start - radial * half_side - transverse * half_side,
    ]
    profile = rg.Polyline(profile_points).ToNurbsCurve()

    sweeps = rg.Brep.CreateFromSweep(rail, profile, False, tolerance)
    if sweeps is None or len(sweeps) == 0:
        raise RuntimeError("The square sweep did not produce a Brep.")
    result = sweeps[0]
    if cap_ends:
        result = result.CapPlanarHoles(tolerance)
        if result is None:
            raise RuntimeError("The swept Brep was created, but its ends could not be capped.")
    return result
