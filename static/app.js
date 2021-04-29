
import { Console, h, Stats } from './smanmi/util.js'
import { Network } from './smanmi/network.js'
import { Monitor, Dump } from './smanmi/monitor.js'

import { Sonar, Css, Debug, Cmd, Subsample, Midi, Actions, Vars, Transients, Image } from './widgets.js'
import { NCA } from './nca.js'
import { Recorder } from './recorder.js'
import { Rec } from './recording.js'
import { Kinect } from './kinect.js'
import { Leds } from './leds.js'

fetch('/defs').then(resp => resp.json()).then(defs => {

  window.console = Console('#console')

  let monitor = Monitor('#monitor', defs)
  let leds = Leds('#leds', defs)

  const record_timestamps = true
  let network = Network('#connection_state', { record_timestamps })

  Dump('#dump', {network})
  Cmd('#cmd', {network, defs})
  Actions('#mode', { name: 'mode', values: defs.modes, network })
  Actions('#animation', { name: 'animation', values: defs.animations, network })
  NCA('#nca', { network, defs })
  Rec('#recording', {network})
  Vars('#vars', {network, defs})
  Actions('#sound', { name: 'scene', values: defs.scenes, network })
  // Subsample('#subsample')
  Sonar('#sonar', {network})
  Kinect('#kinect', {network})
  Css('#css', {network})
  // Recorder('#recorder', {network, defs})
  let midi = Midi('#midi')
  Transients('#transients', {network, defs})
  Image('#kinect_image')

  network
  .listen('animation', Stats('#animation_stats'))
  .listen('animation', leds.listener)
  .listen('signals', Stats('#signals_stats'))
  .listenJson('signals', monitor.listener)
  .listenJson('signals', midi.listener)

  Debug('#debug', { network, record_timestamps })
  midi.sendto(network.sender)

})
