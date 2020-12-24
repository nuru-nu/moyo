
import { Console, h, Stats } from './smanmi/util.js'
import { Network } from './smanmi/network.js'
import { Monitor, Dump } from './smanmi/monitor.js'

import { Sonar, Css, Debug, Cmd, Recorder, Subsample, Midi, Animation, Vars, Sound, Transients } from './widgets.js'
import { Kinect } from './kinect.js'
import { Leds } from './leds.js'

fetch('/defs').then(resp => resp.json()).then(defs => {

  window.console = Console('#console')
  let dump = Dump('#dump')

  let monitor = Monitor('#monitor', defs)
  let leds = Leds('#leds', defs)

  const record_timestamps = true
  let network = Network('#connection_state', { record_timestamps })

  Cmd('#cmd', {network, defs})
  Animation('#animation', {network, defs})
  Vars('#vars', {network, defs})
  Sound('#sound', {network, defs})
  let subsample = Subsample('#subsample')
  let sonar = Sonar('#sonar')
  let kinect = Kinect('#kinect')
  Css('#css', {network})
  let recorder = Recorder('#recorder', defs)
  let midi = Midi('#midi')
  Transients('#transients', {network, defs})

  network
  .listen('animation', Stats('#animation_stats'))
  .listen('animation', leds.listener)
  .listen('signals', Stats('#signals_stats'))
  .listenJson('signals', dump.listener)
  .listenJson('signals', monitor.listener)
  .listenJson('signals', sonar.listener)
  .listenJson('signals', kinect.listener)
  .listenJson('signals', recorder.listener)
  .listenJson('signals', midi.listener)

  Debug('#debug', { network, record_timestamps })
  kinect.sendto(network.sender)
  midi.sendto(network.sender)
  sonar.sendto(network.sender)
  recorder.sendto(network.sender)
  subsample.sendto(network.sender)

})
