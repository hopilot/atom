
from cereal import car, log
from common.conversions import Conversions as CV
from selfdrive.car.hyundai.values import Buttons
from common.numpy_fast import interp
import cereal.messaging as messaging




EventName = car.CarEvent.EventName


class NaviControl():
  def __init__(self, p , CP ):
    self.p = p
    self.CP = CP
    
    self.sm = messaging.SubMaster(['liveNaviData','lateralPlan','radarState','modelV2','longitudinalPlan']) 

    self.btn_cnt = 0
    self.seq_command = 0
    self.target_speed = 0
    self.set_point = 0
    self.wait_timer2 = 0
    self.set_speed_kph = 0
 


    self.gasPressed_time = 0


    self.frame_camera = 0
    self.VSetDis = 30
    self.frame_VSetDis = 30


    self.last_lead_distance = 0


    self.turnSpeedLimitsAhead = 0
    self.turnSpeedLimitsAheadDistances = 0
    self.turnSpeedLimitsAheadDistancesOld = 0

    self.event_navi_alert = None

    self._frame_inc = 0
    self._frame_dec = 0
    self._visionTurnSpeed = 0
    self._current_lat_acc = 0
    self._max_pred_lat_acc = 0

    self.auto_resume_time = 0




  def button_status(self, CS ): 
    if not CS.acc_active or CS.cruise_buttons != Buttons.NONE or CS.out.brakePressed or CS.out.gasPressed: 
      self.wait_timer2 = 50 
    elif self.wait_timer2: 
      self.wait_timer2 -= 1
    else:
      return 1
    return 0


  # buttn acc,dec control
  def switch(self, seq_cmd, CS ):
      self.case_name = "case_" + str(seq_cmd)
      self.case_func = getattr( self, self.case_name, lambda:"default")
      return self.case_func( CS )



  def case_default(self, CS):
      self.seq_command = 0
      return None

  def case_0(self, CS):
      self.btn_cnt = 0
      self.target_speed = self.set_point
      delta_speed = self.target_speed - self.VSetDis

      standstill = CS.out.cruiseState.standstill

      if standstill:
        self.last_lead_distance = 0
        self.seq_command = 5
      elif delta_speed > 1:
        self.seq_command = 1
      elif delta_speed < -1:
        self.seq_command = 2
      return None

  def case_1(self, CS):  # acc
      self.btn_cnt += 1
      if self.target_speed == self.VSetDis:
        self.btn_cnt = 0
        self.seq_command = 3
      elif self.btn_cnt > 10:
        self.btn_cnt = 0
        self.seq_command = 3
      return Buttons.RES_ACCEL


  def case_2(self, CS):  # dec
      self.btn_cnt += 1
      if self.target_speed == self.VSetDis:
        self.btn_cnt = 0
        self.seq_command = 3            
      elif self.btn_cnt > 10:
        self.btn_cnt = 0
        self.seq_command = 3
      return Buttons.SET_DECEL

  def case_3(self, CS):  # None
      self.btn_cnt += 1
      if self.btn_cnt > 6: 
        self.seq_command = 0
      return None

  def case_5(self, CS):  #  standstill
      standstill = CS.out.cruiseState.standstill
      if not standstill:
        self.seq_command = 0
      elif CS.lead_distance < 4:
        self.last_lead_distance = 0
      elif self.last_lead_distance == 0:  
        self.last_lead_distance = CS.lead_distance
      elif CS.lead_distance > self.last_lead_distance:
        self.seq_command = 6
        self.btn_cnt = 0
      return  None


  def case_6(self, CS):  # resume
      self.btn_cnt += 1
      if self.btn_cnt > 5:
        self.btn_cnt = 0
        self.seq_command = 3
      return Buttons.SET_DECEL


  def ascc_button_control( self, CS, set_speed ):
    self.set_point = max(30,set_speed)
    self.curr_speed = CS.out.vEgo * CV.MS_TO_KPH
    self.VSetDis   = CS.VSetDis



    btn_signal = self.switch( self.seq_command, CS )
    return btn_signal


  def get_dRel(self):
      radarState = self.sm['radarState']
      lead_0 = radarState.leadOne
      lead_1 = radarState.leadTwo

      model_v2 = self.sm['modelV2']
      leads_v3 = model_v2.leadsV3
      if lead_0.status:
        dRel1 = self.lead_0.dRel
      else:
        dRel1 = leads_v3[0].x[0]

      if len(leads_v3) > 1:
        dRel2 = leads_v3[1].x[0]
      else:
        dRel2 = 0

      return dRel1, dRel2


  def get_auto_resume(self, CS):
    v_ego_kph = CS.out.vEgo * CV.MS_TO_KPH 
    model_v2 = self.sm['modelV2']
    lanePos = model_v2.position
    distance = 0
    if len(lanePos.x) > 0:
      distance = lanePos.x[-1]

    if distance < 2:
      self.auto_resume_time = 10
    elif  self.auto_resume_time > 0:
      self.auto_resume_time -= 1


    if self.auto_resume_time <= 1 and v_ego_kph < 0.1:
      dRel1 = CS.lead_distance
      if dRel1 > 5 or dRel1 == 0:
        self.event_navi_alert = EventName.manualRestart


    return  distance







  def get_navi_speed(self, sm, CS, cruiseState_speed, frame ):
    cruise_set_speed_kph = cruiseState_speed
    v_ego_kph = CS.out.vEgo * CV.MS_TO_KPH    
    self.liveNaviData = sm['liveNaviData']
    speedLimit = self.liveNaviData.speedLimit
    speedLimitDistance = self.liveNaviData.arrivalDistance  #speedLimitDistance
    #safetySign  = self.liveNaviData.safetySign
    mapValid = self.liveNaviData.mapValid
    trafficType = self.liveNaviData.trafficType
    
    if not mapValid or trafficType == 0:  # ACC
      if cruise_set_speed_kph >  self.VSetDis:
        #if frame % 10 == 0:
        #  cruise_set_speed_kph = self.VSetDis + 1
        if v_ego_kph < (self.VSetDis-5):
          self.frame_camera = frame
          self.frame_VSetDis = self.VSetDis
          cruise_set_speed_kph = self.VSetDis
        else:
          frame_delta = abs(frame - self.frame_camera)
          cruise_set_speed_kph = interp( frame_delta, [0, 2000], [ self.frame_VSetDis, cruise_set_speed_kph ] )
      else:
        self.frame_camera = frame
        self.frame_VSetDis = self.VSetDis

      return  cruise_set_speed_kph

    elif CS.is_highway or speedLimit < 30:
      return  cruise_set_speed_kph
    elif v_ego_kph < 80:
      if speedLimit <= 60:
        spdTarget = interp( speedLimitDistance, [150, 600], [ speedLimit, speedLimit + 30 ] )
      else:      
        spdTarget = interp( speedLimitDistance, [200, 800], [ speedLimit, speedLimit + 40 ] )
    elif speedLimitDistance >= 50:
        spdTarget = interp( speedLimitDistance, [300, 900], [ speedLimit, speedLimit + 50 ] )
    else:
      spdTarget = speedLimit

    if v_ego_kph < speedLimit:
      v_ego_kph = speedLimit

    cruise_set_speed_kph = min( spdTarget, v_ego_kph )
    return  cruise_set_speed_kph


  def auto_speed_control( self, c, CS, ctrl_speed ):
    cruise_set_speed = 0
    if CS.gasPressed:
      self.gasPressed_time = 100
    elif self.gasPressed_time > 0:
      self.gasPressed_time -= 1
      if self.gasPressed_time <= 0:
        cruise_set_speed = CS.clu_Vanz - 5
    elif CS.cruise_set_mode == 2:  # comma long control speed.
      vFuture = c.hudControl.vFuture * CV.MS_TO_KPH
      ctrl_speed = min( vFuture, ctrl_speed )



    if cruise_set_speed > 30:
      CS.set_cruise_speed( cruise_set_speed )  

    return  ctrl_speed


  def update(self, c, CS, frame ):  
    self.sm.update(0)
    # send scc to car if longcontrol enabled and SCC not on bus 0 or ont live
    btn_signal = None
    if not self.button_status( CS  ):
      pass
    elif CS.acc_active:
      cruiseState_speed = CS.out.cruiseState.speed * CV.MS_TO_KPH      
      kph_set_vEgo = self.get_navi_speed(  self.sm , CS, cruiseState_speed, frame )
      self.ctrl_speed = min( cruiseState_speed, kph_set_vEgo)

      if CS.cruise_set_mode:
        self.ctrl_speed = self.auto_speed_control( c, CS, self.ctrl_speed )


      self.set_speed_kph = self.ctrl_speed
      btn_signal = self.ascc_button_control( CS, self.ctrl_speed )

    return btn_signal
