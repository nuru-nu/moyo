
import { h, u, debounce } from './smanmi/util.js'
// import { DiscreteInterpolant } from './threejs/three.module.js'
import { Header } from './widgets.js'

const secs_to_timestr = secs => new Date(1000 * secs).toTimeString().substr(0, 8)

const secs_to_human = secs => {
  let s = ''
  if (secs > 3600) {
    s += `${Math.floor(secs/3600)}h`
    secs %= 3600
  }
  if (secs > 60) {
    s += `${Math.floor(secs/60)}m`
    secs %= 60
  }
  secs = Math.round(secs)
  if (secs) {
    s += `${secs}s`
  }
  return s
}

const Progressbar = () => {
  const disp = h.div('cont', { class: 'flex' }).of(
    h.span('start').of('00:00:00'),
    h.input('range', { type: 'range', min: 0, max: 1, step: 0.001, style: 'flex-grow:1' }),
    h.span('stop').of('00:00:00'),
  ).els
  const listeners = new Set()
  let rec = null
  disp.range.addEventListener('input', e => {
    const x = parseFloat(e.target.value)
    const t = rec.start + x * (rec.stop - rec.start)
    Array.from(listeners).forEach(listener => listener(t))
  })
  return {
    el: disp.cont,
    change: listener => listeners.add(listener),
    set: rec_ => {
      rec = rec_
      disp.start.textContent = secs_to_timestr(rec.start)
      disp.stop.textContent = secs_to_timestr(rec.stop)
    },
    sett: t => {
      const x = Math.min(1, Math.max(0,
        (t - rec.start) / (rec.stop - rec.start)))
      disp.range.value = x
    }
  }
}

export const Rec = (output, { network }) => {
  const pbar = Progressbar()
  const disp = Header('rec', h.div('.widget').of(
    h.div('idle').of(
      h.button('record', { style: 'color:red' }).of('● rec'),
      h.button('play').of('▶ play'),
      ),

      h.div('choice').of(
        h.select('recs'), ' ',
        h.button('play2').of('▶ play'), ' ',
        h.button('cancel').of('cancel'),
    ),

    h.div('recording').of(
      h.div().of(
        h.span({ style: 'color:red;', class: 'blink' }).of('● rec'), ' ',
        h.span('rec_start').of('00:00:00'), '..',
        h.span('rec_at').of('00:00:00'), ' ',
        h.button('stop1').of('■ stop'),
      ),
    ),

    h.div('playing').of(
      h.div().of(
        h.span({ class: 'blink' }).of('▶ play'), ' ',
        h.span('play_at').of('00:00:00'), ' ',
        h.button('stop2').of('■ stop'),
      ),
      pbar.el,
      h.div('signals').of(),
    ),

    h.div('common').of(
      h.div().of(
        'id=', h.span('id'),
        ' name: ', h.input('name', { type: 'text' }),
      ),
      h.div().of('comments:'),
      h.textarea('comments', { class: 'comments' }),
    ),

  )).into(output).els

  function show() {
    const which = new Set(arguments);
    ['idle', 'recording', 'choice', 'playing', 'common'].forEach(name => {
      disp[name].classList[which.has(name) ? 'remove' : 'add']('h')
    })
  }
  show('idle')

  let loading = false
  let loading_promise = null
  let recs = null
  function reload() {
    if (loading) return loading_promise
    loading = true
    loading_promise = new Promise((resolve, reject) => {
      network.fetch('/recs').then(resp => resp.json()).then(recs_ => {
        recs = recs_
        loading = false
        resolve()
      }).catch(err => {
        loading = false
        recs = []
        reject(err)
      })
    })
    return loading_promise
  }
  reload()

  // record
  disp.record.addEventListener('click', e => {
    const now = new Date().toISOString()
    const ident = now.replace(/[:-]/g, '').replace('T', '_').slice(0, 13)
    network.sender({rec_action: `start=${ident}`})
  })
  disp.stop1.addEventListener('click', e => {
    update_name()
    update_comments()
    network.sender({rec_action: 'stop'})
  })

  // choice
  disp.play.addEventListener('click', e => {
    reload().then(() => {
      u.empty(disp.recs)
      recs.forEach(rec => {
        const duration = secs_to_human(rec.stop - rec.start)
        const text = `${rec.id} - ${duration} - ${rec.name}`
        h.option({value: rec.id}).of(text).into(disp.recs)
      })
      show('choice')
    })
  })

  // playback
  disp.play2.addEventListener('click', e => {
    if (!disp.recs.value) return
    network.sender({rec_action: `play=${disp.recs.value}`})
  })
  disp.cancel.addEventListener('click', () => show('idle'))
  disp.stop2.addEventListener('click', e => {
    update_name()
    update_comments()
    network.sender({rec_action: 'stop'})
  })
  pbar.change(t => {
    network.sender({rec_action: `t=${t - play.start}`})
  })

  let play = null  // (obj) currently playing
  let signals = {}  // buttons of currently enabled signals
  let start = null  // (secs) set if currently recording

  // common
  function update_name() {
    network.sender({ rec_action: `name=${disp.name.value}` })
  }
  function update_comments() {
    network.sender({ rec_action: `comments=${disp.comments.value}` })
  }
  disp.name.addEventListener('keyup', () => debounce(update_name, 3000))
  disp.comments.addEventListener('keyup', () => debounce(update_comments, 3000))

  network.listenJson('signals', data => {
    if (loading) return
    if (data.rec_state && data.rec_state.play) {
      // playback
      if (!play || play.id !== data.rec_state.play) {
        // start playing
        play = recs.filter(rec => rec.id === data.rec_state.play)[0]
        pbar.set(play)
        disp.id.textContent = data.rec_state.play
        disp.name.value = play.name
        disp.comments.value = play.comments
        u.empty(disp.signals)
        play.signals.forEach(signal => {
          const button = h.button().of(signal).into(disp.signals).el
          button.addEventListener('click',
            () => network.sender({ rec_action: `toggle=${signal}` }))
          signals[signal] = button
        })
        show('playing', 'common')
      }
      const enabled = new Set(data.rec_state.enabled)
      Object.keys(signals).forEach(
        signal => signals[signal].classList[
          enabled.has(signal) ? 'add' : 'remove']('on'))
      pbar.sett(data.rec_state.t)
      disp.play_at.textContent = secs_to_timestr(data.rec_state.t)
    }
    if (data.rec_state && data.rec_state.start) {
      // recording
      if (!start) {
        // start recording
        start = data.rec_state.start
        disp.id.textContent = '(NEW)'
        disp.name.value = ''
        disp.comments.value = ''
        show('recording', 'common')
        disp.rec_start.textContent = secs_to_timestr(start)
      }
      disp.rec_at.textContent = secs_to_timestr(data.t)
    }
    if (play && (!data.rec_state || !data.rec_state.play)) {
      // stop playing
      play = null
      show('idle')
    }
    if (start && (!data.rec_state || !data.rec_state.start)) {
      // stop recording
      start = null
      show('idle')
    }
  })
}
