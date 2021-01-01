
import { Dump } from './smanmi/monitor.js'
import { Transients } from './widgets.js'
import { Kinect } from './kinect.js'
import { Rec } from './recording.js'

const recs = [
  {
    id: '20201231_1830', name: 'first recording',
    start: new Date(2020, 12 - 1, 31, 18, 30).getTime() / 1000,
    stop: new Date(2020, 12 - 1, 31, 19, 30).getTime() / 1000,
    signals: ['sonar_sensor', 'people_sensor', 'sonar_override', 'people_override'],
    comments: '',
  },
  {
    id: '20210101_1125', name: 'second recording',
    start: new Date(2021, 1 - 1, 1, 11, 25).getTime() / 1000,
    stop: new Date(2021, 1 - 1, 1, 12, 25).getTime() / 1000,
    signals: ['sonar_sensor', 'people_sensor', 'sonar_override', 'people_override'],
    comments: '',
  },
]

const secs_to_id = secs => new Date(1000 * secs).toISOString().replace(/[:-]/g, '').replace('T', '_').substr(0, 13)

const defs = {
  monitor_def: {
    transients: ['rec_action'],
  },
}

const network = function () {
  const data = {
    signals: {
      t: Date.now() / 1000,
      // kinect
      people: [],
      // rec
      rec_state: null,
    },
  }
  const transients = new Map()
  defs.monitor_def.transients.forEach(transient => transients.set(transient, []))

  const listeners = { signals: new Set() }

  let play = null  // (obj) currently playing
  let ongoing = null  // (obj) currently recording
  const ms = 50
  function tick() {
    data.signals.t += ms / 1000
    if (play && data.signals.t > play.stop) data.signals.t = play.start
    Array.from(transients.keys()).forEach(transient => {
      const l = transients.get(transient)
      if (l.length) {
        data.signals[transient] = l.shift()
      } else {
        delete data.signals[transient]
      }
    })
    Array.from(listeners.signals).forEach(listener => listener(data.signals))
    setTimeout(tick, ms)
  }
  tick()

  function sender(dict) {
    const signals = data.signals
    Object.keys(signals).forEach(
      key => dict.hasOwnProperty(key) && (signals[key] = dict[key]))
    Array.from(transients.keys()).forEach(transient => {
      if (dict.hasOwnProperty(transient)) {
        transients.get(transient).push(dict[transient])
      }
    })
    // kinect
    if (signals.people_override) signals.people = signals.people_override
    // recording
    if (dict.rec_action) {
      let m = dict.rec_action.match(/^play=(.*)/)
      if (m) {
        play = recs.filter(rec => rec.id === m[1])[0]
        signals.rec_state = {
          play: play.id,
          enabled: [],
        }
        signals.t = play.start
      }
      m = dict.rec_action.match(/^toggle=(.*)/)
      if (play && m) {
        const enabled = new Set(signals.rec_state.enabled)
        if (enabled.has(m[1])) {
          enabled.delete(m[1])
        } else {
          enabled.add(m[1])
        }
        signals.rec_state.enabled = Array.from(enabled)
      }
      m = dict.rec_action.match(/^t=(.*)/)
      if (play && m) {
        const t = Math.min(play.stop, Math.max(play.start, parseFloat(m[1])))
        data.signals.t = t
      }
      m = dict.rec_action.match(/^name=(.*)/)
      if (m) {
        if (play) play.name = m[1]
        if (ongoing) ongoing.name = m[1]
      }
      m = dict.rec_action.match(/^comments=(.*)/)
      if (m) {
        if (play) play.comments = m[1]
        if (ongoing) ongoing.comments = m[1]
      }
      if (dict.rec_action === 'start') {
        play = null
        signals.t = Date.now() / 1000
        ongoing = { id: secs_to_id(signals.t), start: signals.t, name: '', comments: '' }
        signals.rec_state = { start: signals.t }
      }
      if (dict.rec_action === 'stop') {
        if (play) {
          play = null
          signals.t = Date.now() / 1000
        }
        if (ongoing) {
          ongoing.stop = signals.t
          ongoing.signals = recs[0].signals
          recs.push(ongoing)
          ongoing = null
        }
        signals.rec_state = null
      }
    }
  }

  function fetch(path) {
    if (path === '/recs') {
      return Promise.resolve(JSON.parse(JSON.stringify(recs)))
    }
    return Promise.reject()
  }

  return {
    listenJson: function (which, listener) {
      listeners[which].add(listener)
    },
    sender,
    fetch,
  }
}()

// Kinect('#test', { network })
Rec('#test', { network })
Dump('#dump', { network })
Transients('#dump', { network, defs })
