import pathlib
from typing import List, Final
import time
import numpy as np
import pandas as pd
import tensorflow as tf
import copy
from multiprocessing import Pool
from waymo_open_dataset.protos import scenario_pb2, map_pb2
from trajdata.proto import vectorized_map_pb2

WAYMO_DT: Final[float] = 0.1
SOURCE_DIR = "../../../../../scenarios"
WAYMO_DATASET_NAMES = ["testing",
                 "testing_interactive",
                 "training",
                 "training_20s",
                 "validation",
                 "validation_interactive"]
from trajdata.data_structures.agent import (
    Agent,
    AgentMetadata,
    AgentType,
    FixedExtent, VariableExtent
)

def parse_data(data):
    scenario = scenario_pb2.Scenario()
    scenario.ParseFromString(data)
    return scenario
class WaymoScenarios:
    def __init__(self, dataset_name, source_dir=SOURCE_DIR, load=True, num_parallel_reads=None):
        if dataset_name not in WAYMO_DATASET_NAMES:
            raise RuntimeError('Wrong dataset name. Please choose name from '+str(WAYMO_DATASET_NAMES))
        self.name = dataset_name
        self.source_dir = source_dir
        self.scenarios = []
        if load:
            self.load_scenarios(num_parallel_reads)
    def load_scenarios(self, num_parallel_reads, verbose=True):
        self.scenarios = []
        source_it = pathlib.Path().glob(self.source_dir+'/'+self.name + "/*.tfrecord")
        file_names = [str(file_name) for file_name in source_it if file_name.is_file()]
        if verbose:
            print("Loading tfrecord files...")
        dataset = tf.data.TFRecordDataset(file_names, compression_type='', num_parallel_reads=num_parallel_reads).as_numpy_iterator()

        if verbose:
            print("Converting to protobufs...")
        start = time.perf_counter()
        dataset = np.fromiter(dataset, bytearray)
        # use multiprocessing:
        # self.scenarios = Pool().map(parse_data, dataset)
        # use np vectorization (faster in my computer):
        parser = np.vectorize(parse_data)
        self.scenarios = parser(dataset)
        print(time.perf_counter()-start)
        if verbose:
            print(str(len(self.scenarios)) + " scenarios from " + str(len(file_names)) + " file(s) have been loaded successfully")


# way = WaymoScenarios(dataset_name='haha')
def translate_agent_type(type):
    if type == scenario_pb2.Track.ObjectType.TYPE_VEHICLE:
        return AgentType.VEHICLE
    if type == scenario_pb2.Track.ObjectType.TYPE_PEDESTRIAN:
        return AgentType.PEDESTRIAN
    if type == scenario_pb2.Track.ObjectType.TYPE_CYCLIST:
        return AgentType.BICYCLE
    if type == scenario_pb2.Track.ObjectType.OTHER:
        return AgentType.UNKNOWN
    return -1


def translate_poly_line(polyline: List[map_pb2.MapPoint]) -> vectorized_map_pb2.Polyline:
    ret = vectorized_map_pb2.Polyline()
    for point in polyline:
        ret.dx_mm.add(round(point.x * 100))
        ret.dy_mm.add(round(point.y * 100))
        ret.dz_mm.add(round(point.z * 100))
    return ret


def translate_lane(lane: map_pb2.LaneCenter) -> vectorized_map_pb2.RoadLane:
    ret = vectorized_map_pb2.RoadLane
    ret.left_boundary = translate_poly_line(lane.polyline[lane.left_bounaries.lane_start_index:lane.left_bounaries.lane_end_index])
    ret.right_boundary = translate_poly_line(lane.polyline[lane.right_bounaries.lane_start_index:lane.right_bounaries.lane_end_index])
    ret.entry_lanes = lane.entry_lanes
    ret.exit_lanes = lane.exit_lanes
    ret.adjacent_lanes_left = [neighbor.feature_id for neighbor in lane.left_neighbors]
    ret.adjacent_lanes_right = [neighbor.feature_id for neighbor in lane.right_neighbors]
    return ret


def translate_crosswalk(lane: map_pb2.Crosswalk) -> vectorized_map_pb2.PedCrosswalk:
    ret = vectorized_map_pb2.PedCrosswalk()
    ret.polygon = translate_poly_line(lane.polygon)
    return ret


# agent_list: List[AgentMetadata] = []
# agent_presence: List[List[AgentMetadata]] = [
#     [] for _ in range(91)
# ]
# scenario = load_tfrecords(data_dir + '/training', False)[0]
# agent_ids = []
# agent_translations = []
# agent_velocities = []
# agent_yaws = []
# agent_ml_class = []
# agent_sizes = []
#
# for index, track in enumerate(scenario.tracks):
#     agent_name = track.id
#     if index == scenario.sdc_track_index:
#         agent_name = "ego"
#
#     agent_ids.append(agent_name)
#
#     agent_type: AgentType = translate_agent_type(track.object_type)
#     agent_ml_class.append(agent_type)
#     states = track.states
#     translations = [[state.center_x, state.center_y, state.center_z] for state in states]
#     agent_translations.extend(translations)
#     velocities = [[state.velocity_x, state.velocity_y] for state in states]
#     agent_velocities.extend(velocities)
#     sizes = [[state.length, state.width, state.height] for state in states]
#     agent_sizes.extend(sizes)
#     yaws = [state.heading for state in states]
#     agent_yaws.extend(yaws)
#
#     first_timestep = 0
#     states = track.states
#     for timestep in range(91):
#         if states[timestep].valid:
#             first_timestep = timestep
#             break
#     last_timestep = 90
#     for timestep in range(91):
#         if states[90 - timestep].valid:
#             last_timestep = timestep
#             break
#
#     agent_info = AgentMetadata(
#         name=agent_name,
#         agent_type=agent_type,
#         first_timestep=first_timestep,
#         last_timestep=last_timestep,
#         extent=VariableExtent(),
#     )
#     if last_timestep - first_timestep != 0:
#         agent_list.append(agent_info)
#
#     for timestep in range(first_timestep, last_timestep + 1):
#         agent_presence[timestep].append(agent_info)
#
# agent_ids = np.repeat(agent_ids, 91)
#
# agent_translations = np.array(agent_translations)
# agent_velocities = np.array(agent_velocities)
# agent_sizes = np.array(agent_sizes)
#
# agent_ml_class = np.repeat(agent_ml_class, 91)
# agent_yaws = np.array(agent_yaws)
#
# print(agent_ids.shape)
# print(agent_translations.shape)
# print(agent_velocities.shape)
# print(agent_sizes.shape)
# print(agent_ml_class.shape)
# print(agent_yaws.shape)
#
# all_agent_data = np.concatenate(
#     [
#         agent_translations,
#         agent_velocities,
#         np.expand_dims(agent_yaws, axis=1),
#         np.expand_dims(agent_ml_class, axis=1),
#         agent_sizes,
#     ],
#     axis=1,
# )
#
# traj_cols = ["x", "y", "z", "vx", "vy", "heading"]
# class_cols = ["class_id"]
# extent_cols = ["length", "width", "height"]
# agent_frame_ids = np.resize(
#     np.arange(91), 63*91
# )
#
# all_agent_data_df = pd.DataFrame(
#     all_agent_data,
#     columns=traj_cols + class_cols + extent_cols,
#     index=[agent_ids, agent_frame_ids],
# )
#
# all_agent_data_df.index.names = ["agent_id", "scene_ts"]
# all_agent_data_df.sort_index(inplace=True)
# all_agent_data_df.reset_index(level=1, inplace=True)
#
# all_agent_data_df[["ax", "ay"]] = (
#         arr_utils.agent_aware_diff(
#             all_agent_data_df[["vx", "vy"]].to_numpy(), agent_ids
#         )
#         / WAYMO_DT
# )
# final_cols = [
#                  "x",
#                  "y",
#                  "vx",
#                  "vy",
#                  "ax",
#                  "ay",
#                  "heading",
#              ] + extent_cols
# all_agent_data_df.reset_index(inplace=True)
# all_agent_data_df["agent_id"] = all_agent_data_df["agent_id"].astype(str)
# all_agent_data_df.set_index(["agent_id", "scene_ts"], inplace=True)
#
# print(all_agent_data_df)
# print(all_agent_data_df.columns)
# print(all_agent_data_df.loc[:, final_cols])
# print(pd.concat([all_agent_data_df.loc[:, final_cols]]))
# print(scenario.tracks[0].id)
# print(scenario.tracks[0].states[1].height)

# for track in scenario.tracks:
#
#     print(all_agent_data_df['height'][str(track.id)][0])
#     break
