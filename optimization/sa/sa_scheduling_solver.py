from typing import Tuple, List, Dict

from ortools.sat.python.cp_model import (FEASIBLE, INFEASIBLE, MODEL_INVALID,
                                         OPTIMAL, UNKNOWN, CpModel, CpSolver)

from input.model.schedule import schedule
from input.model.task import task
from input.model.application import application
from input.testcase import Testcase
from input.input_parameters import InputParameters
from solution.solution_optimization_status import EOptimizationStatus
from solution.solution_timing_data import TimingData
from utils.utilities import Timer, list_gcd, print_model_stats


class SASchedulingSolver:
    def __init__(self, tc: Testcase, timing_object: TimingData):
        self.tc = tc

        # Create the model_old
        self.model = CpModel()

        # Create variables
        t = Timer()
        with t:
            self._create_variables()
        timing_object.time_creating_vars_pint = t.elapsed_time


    def _create_variables(self):
        self.Pint_var = self.model.NewIntVar(0, self.tc.hyperperiod, "Pint")

    def _task_finish_time(self, t: task, task_start_times: Dict[str, int]):
        return task_start_times[t.id] + t.exec_time

    def _stream_finish_time(self, t1: task, t2: task, t_start_times: Dict[str, int]):
        if t1.src_es_id == t2.src_es_id:
            c_signal = 0
        else:
            app = self.tc.A[t1.app_id]
            stream = self.tc.F_routed[app.edges_from_nodes[t1.id][t2.id][0]]
            route = self.tc.R[stream.id]
            c_signal = 0
            for l in route.get_links_along_route_towards(t2.src_es_id, self.tc.L_from_nodes):
                c_signal += l.transmission_length(stream.size)

        return self._task_finish_time(t1, t_start_times) + c_signal

    def _es_finish_time(self, es_id: str, t_start_times: Dict[str, int]):
        finish_time = 0
        for t_id, start_time in t_start_times.items():
            t = self.tc.T[t_id]
            if es_id == t.src_es_id:
                if self._task_finish_time(t, t_start_times) > finish_time:
                    finish_time = self._task_finish_time(t, t_start_times)

        return finish_time

    def _data_ready_time(self, t: task, t_start_times: Dict[str, int]):
        """
        Returns the data ready time for a given task_id
        """
        app = self.tc.A[t.app_id]
        predecessor_finish_times = [self._stream_finish_time(self.tc.T[t_i_id], t, t_start_times) for t_i_id in app.get_predecessors_ids(t.id)]
        if len(predecessor_finish_times) == 0:
            tdr = 0
        else:
            tdr = max(predecessor_finish_times)
        return tdr

    def _list_schedule(self, sorted_task_list: List[str]):
        t_start_times: Dict[str, int] = {}
        for task_id in sorted_task_list:
            # End Technique
            task = self.tc.T[task_id]
            t_start_times[task_id] = max(self._data_ready_time(task, t_start_times), self._es_finish_time(task.src_es_id, t_start_times))
        return t_start_times

    def _solve(self):
        # create initial ordering
        for app in self.tc.A_app.values():
            order = app.get_topological_order()
            t_start_times = self._list_schedule(order)
            print(t_start_times)
        return t_start_times

    def optimize(
        self, input_params: InputParameters, timing_object: TimingData
    ) -> Tuple[Testcase, EOptimizationStatus]:

        status = EOptimizationStatus.FEASIBLE
        t = Timer()
        with t:
            # OPTIMIZE
            start_times = self._solve()
        timing_object.time_optimizing_pint = t.elapsed_time



        if (status == EOptimizationStatus.FEASIBLE):
            # UPDATE tc
            self.tc.schedule = schedule()
        else:
            raise ValueError(
                "CPSolver returned invalid status for SAScheduling model_old: " + str(status)
            )
        return self.tc, status
