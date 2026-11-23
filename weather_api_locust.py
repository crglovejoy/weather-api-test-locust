import random
import logging
import gevent
import os

from pathlib import Path
from locust import HttpUser, between, task, events
from threading import Lock
from data_source import load_csv_and_return_list_of_class_objects, weather_location


##########################
##  TEST CLASS WEATHER  ##
##########################
## Example URL: https://api.weather.gov/points/39.7456,-97.0892

class Weather(HttpUser):
    wait_time = between(2, 5)
    host = "https://api.weather.gov/points/"
    weather_coordinates_list = list[weather_location]
    weather_coordinates_list_len = 0
    get_weather_coordiantes_lock = Lock()



    ######################################
    ##  On Start Executed By Each User  ##
    ######################################
    # let the first user load the test data from file while other users wait for the data to be available to them.
    def on_start(self):
        try:
            if self.weather_coordinates_list_len == 0:
                with self.get_weather_coordiantes_lock:
                    if self.weather_coordinates_list_len == 0:
                        self.weather_coordinates_list = load_csv_and_return_list_of_class_objects(
                            "weather_location", 
                            f"{Path.cwd()}{os.path.sep}weather_loc_input.csv", 
                            True
                        )
                        self.weather_coordinates_list_len = len(self.weather_coordinates_list)

                if self.weather_coordinates_list_len == 0:
                    raise Exception("the data source provided an empty input data list")
        except Exception as e:
            self.stop_the_test_on_except(e)


    ###############################
    ##  Get Weather Test Method  ##
    ###############################

    @task
    def get_weather(self):
        new_loc: weather_location = self.weather_coordinates_list[random.randint(0, self.weather_coordinates_list_len - 1)]

        with self.client.get(
            f"{new_loc.latitude},{new_loc.longitude}",
            name=f"request_{new_loc.city.lower()}_{new_loc.state.lower()}", 
            catch_response=True
        ) as response:
            if response.status_code == 200:
                resp_city, resp_state = self.get_city_state_from_response(response)
                if resp_city == new_loc.city and resp_state == new_loc.state:
                    response.success()
                else:
                    response.failure(f"Status code was {response.status_code} but {resp_city} != {new_loc.city} and/or {resp_state} != {new_loc.state} in the response:{response.text}")      
            else:
                response.failure(f"Unexpected status code: {response.status_code}")


    ################################
    ##  Response Data Extractors  ##
    ################################

    @staticmethod
    def get_city_state_from_response(resp: HttpUser.ResponseContextManager) -> tuple[str, str]:
        try:
            data = resp.json()
            return (
                data.get("properties").get("relativeLocation").get("properties").get("city"), 
                data.get("properties").get("relativeLocation").get("properties").get("state")
            )
        except Exception as e:
            return None, None


    ######################################
    ##  Test Stoppage on Error Methods  ##
    ######################################
        
    def stop_the_test_on_except(self, e: Exception):
        logging.exception({e})
        self.flush_the_logs_and_stop_testing()
    
    def flush_the_logs_and_stop_testing(self):
        # flush the logs and wait .5 secs before we stop the test so logging can catch up.
        for handler in logging.getLogger().handlers:
            handler.flush()
        gevent.sleep(0.5)
        self.environment.runner.quit()


######################################
##  TEST RESULT THRESHOLD ANALYSIS  ##
######################################

def handle_greater_than_err_checking_and_return_fail_bool(fail_msg_list: list[str], context_name: str, metric: str, val: float, threshold: float) -> bool:
    if val > threshold:
        fail_msg_list.append(f"Test failed because {context_name} {metric} was too high: {val} > {threshold}")
        return True
    return False

avg_response_thresholds_dict: dict[str, float] = {
    "request_allen_tx": 60,
    "request_bemidji_mn": 60,
    "request_burlington_vt": 80,
    "request_linn_ks": 60,
    "request_oxford_ms": 85,
    "request_oxnard_ca": 65
}

@events.quitting.add_listener
def _(environment, **kw):
    fail: bool = False
    fail_msg_list: list[str] = []

    # make sure we had request stats to analyze
    if environment.stats.total.num_requests == 0:
        fail_msg_list.append(f"Test failed due to 0 requests being made")
        fail = True
    else:
        # check the overall failure rate
        fail = fail or handle_greater_than_err_checking_and_return_fail_bool(
            fail_msg_list, 
            "total failure %", 
            "total.fail_ratio", 
            environment.stats.total.fail_ratio, 
            0.01
        )

        # check the avg response time for each request name against the threshold value
        # contained in the avg_response_thresholds_dict dictionary.
        for (name, method), stats_entry in environment.stats.entries.items():
            thresh_val = avg_response_thresholds_dict.pop(name, None)

            if not thresh_val:
                fail = True
                fail_msg_list.append(f"{name} does not have a avg_respose_time threshold defined")
            else:
                fail = fail or handle_greater_than_err_checking_and_return_fail_bool(
                    fail_msg_list,
                    name,
                    "avg_response_time",
                    stats_entry.avg_response_time,
                    thresh_val
                )

        # anything left in the dictionary means we did not encounter the key/name in the stats
        for key in avg_response_thresholds_dict.keys():
            fail = True
            fail_msg_list.append(f"Did not find an instance of {key} in the results to do threshold analysis")

    if fail:
        for msg in fail_msg_list:
            logging.error(msg)
        environment.process_exit_code = 1
    else:
        logging.info("All threshold analysis PASSED")
        environment.process_exit_code = 0



        
