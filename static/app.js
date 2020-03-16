
import { Console, h, Stats } from './smanmi/util.js'
import { Network } from './smanmi/network.js'
import { Monitor } from './smanmi/monitor.js'

import { Sonar, Debug, Cmd } from './widgets.js'
import { Leds } from './leds.js'

window.console = Console('#console')

let monitor = Monitor('#monitor', {
  presets: {
    default: new Set(['loud', 'low', 'high']),
    states: new Set(['drone1', 'drone2', 'into']),
  },
})
let leds = Leds('#leds')

const record_timestamps = true

let cmd = Cmd('#controls')
let sonar = Sonar('#controls')

let network = Network('#connection_state', { record_timestamps })
.listen('animation', Stats('#animation_stats'))
.listen('animation', leds.listener)
.listen('signals', Stats('#signals_stats'))
.listen('signals', monitor.listener)
.listen('signals', sonar.listener)

Debug('#controls', { network, record_timestamps })
sonar.sendto(network.sender)
cmd.sendto(network.sender)
