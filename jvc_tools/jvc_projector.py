#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""JVC projector high level module"""

from .jvc_command import(JVCCommand, Command, SourceData, PowerState, LowLatency, CommandNack)
import logging
_LOGGER = logging.getLogger(__name__)

NORMAL_INPUTS = {'HDMI 1': 'HDMI1', 'HDMI 2': 'HDMI2'}
STATE_ON = "on"
STATE_OFF = "off"
STATE_COOLING = "cooling"
STATE_STARTING = "starting"
STATE_UNKNOWN = "unknown"

class JVCProjector:
    def __init__(self, host):
        self._host = host
        self._jvc = JVCCommand(host=host)
        self._powerState = PowerState.StandBy
        self._lowLatencyState = LowLatency.Off
        self._input_info = STATE_UNKNOWN

    @property 
    def state(self):            
        if (self._powerState == PowerState.LampOn):
            return STATE_ON
        if (self._powerState == PowerState.StandBy):
            return STATE_OFF
        if (self._powerState == PowerState.Cooling):
            return STATE_COOLING
        if (self._powerState == PowerState.Starting):
            return STATE_STARTING

        return STATE_UNKNOWN   

    def turn_on(self):
        """Turn the media player on."""
        with self._jvc as cmd:          
            try:  
                currentState = cmd.get(Command.Power)
                if currentState == PowerState.StandBy:
                    cmd.set(Command.Power, PowerState.LampOn)
                    self._powerState = PowerState.LampOn
                else:
                    _LOGGER.debug('Projector was not in standby, could not turn on. State: %s', currentState)
            except Exception as err:
                _LOGGER.error('Failed to turn on the projector.', err)
                return False
            else:
                return True

    def turn_off(self):
        """Turn the media player on."""
        with self._jvc as cmd:          
            try:  
                currentState = cmd.get(Command.Power)
                if currentState == PowerState.LampOn:
                    cmd.set(Command.Power, PowerState.StandBy)
                    self._powerState = PowerState.StandBy
                else:
                    _LOGGER.debug('Projector was not ON, could not turn Off. State: %s', currentState)
            except Exception as err:
                _LOGGER.error('Failed to turn off the projector.', err)
                return False
            else:
                return True


    @property 
    def low_latency_enabled(self):
        return self._lowLatencyState == LowLatency.On

    @low_latency_enabled.setter
    def low_latency_enabled(self, enabled): 
        with self._jvc as cmd:              
            desiredLowLatency = LowLatency.On if enabled else LowLatency.Off
            try:                    
                currentState = cmd.get(Command.Power)
                if currentState != PowerState.LampOn:
                    _LOGGER.info('Projector was not in the correct state (LampOn). Current State: %s', currentState)
                    return False
                cmd.set(Command.LowLatency, desiredLowLatency)
            except CommandNack as err:
                _LOGGER.error('Error communicating with projector', err)
                return False
            else:
                _LOGGER.info('LowLatency state set to %s', enabled)
                self._lowLatencyState = desiredLowLatency
                
    @property    
    def input_info(self):
        return self._input_info

    def _update(self, retry=2):
        try:
            with self._jvc as cmd:  
                _LOGGER.debug('Updating projector. Tries remaining: %d', retry)
                try:                    
                    self._powerState = cmd.get(Command.Power)
                except Exception as err:
                    if retry < 1:
                        _LOGGER.error("Exception getting power state:", err)  
                        return False
                    return self._update(retry - 1)
                else:
                    _LOGGER.debug('Power on, reading other properties.')
                    self._lowLatencyState = None
                    if (self._powerState == PowerState.LampOn):
                        """Only try to get other states if the lamp is on, otherwise it is rejected."""
                        self._lowLatencyState = cmd.get(Command.LowLatency) 
                        self._input_info = cmd.get(Command.InfoSource)
                    return False           
        except CommandNack as err:
            if retry < 1:
                _LOGGER.error("NACK during update:", err)  
                return False
            return self._update(retry - 1)       
        except Exception as err:
            if retry < 1:
                _LOGGER.error("Generic error during update:", err)
                return False        
            return self._update(retry - 1)

    def update(self):
        self._update()