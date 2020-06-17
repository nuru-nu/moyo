
import { Console, h, Stats } from './smanmi/util.js'
import { Network } from './smanmi/network.js'
import { Monitor, Dump } from './smanmi/monitor.js'

import { Sonar, Css, Debug, Cmd, Recorder, Subsample, Midi, Animation, Sound } from './widgets.js'
import { Kinect } from './kinect.js'
import { Leds } from './leds.js'

fetch('/defs').then(resp => resp.json()).then(defs => {

  window.console = Console('#console')
  let dump = Dump('#dump')

  let monitor = Monitor('#monitor', {
    presets: {
      default: new Set(['loud', 'low', 'high']),
      states: new Set(['drone1', 'drone2', 'into']),
    },
  })
  let leds = Leds('#leds', defs)

  const record_timestamps = true

  let cmd = Cmd('#cmd', defs)
  let animation = Animation('#animation', defs)
  let sound = Sound('#sound', defs)
  let subsample = Subsample('#subsample')
  let sonar = Sonar('#sonar')
  let kinect = Kinect('#kinect')
  let css = Css('#kinect')
  let recorder = Recorder('#recorder', defs)
  let midi = Midi('#midi')

  let network = Network('#connection_state', { record_timestamps })
  .listen('animation', Stats('#animation_stats'))
  .listen('animation', leds.listener)
  .listen('signals', Stats('#signals_stats'))
  .listenJson('signals', dump.listener)
  .listenJson('signals', monitor.listener)
  .listenJson('signals', sonar.listener)
  .listenJson('signals', kinect.listener)
  .listenJson('signals', css.listener)
  .listenJson('signals', recorder.listener)
  .listenJson('signals', midi.listener)

  Debug('#debug', { network, record_timestamps })
  cmd.sendto(network.sender)
  animation.sendto(network.sender)
  sound.sendto(network.sender)
  kinect.sendto(network.sender)
  css.sendto(network.sender)
  midi.sendto(network.sender)
  sonar.sendto(network.sender)
  recorder.sendto(network.sender)
  subsample.sendto(network.sender)

})
