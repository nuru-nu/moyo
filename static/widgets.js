import { h, u, ui, colors, Lines } from './smanmi/util.js'

export const Sonar = (output) => {
  const disp = h.div({class: 'flex widget'}).of(
    h.div({class: 'header'}).of('sonar'),
    h.button('override').of('override'),
    h.input('sonar', {type: 'range', min: -1, max: 50, value: 50}),
  ).into(output).els

  let override = false
  disp.sonar.style.display = 'none'
  disp.override.addEventListener('click', () => {
    override = !override
    disp.override.classList.toggle('on')
    disp.sonar.style.display = override ? 'block' : 'none'
    update()
  })
  disp.sonar.addEventListener('change', update)

  let sender
  function update() {
    if (!override) {
      if (sender) sender({sonar: null})
      return
    }
    if (sender) sender({sonar: parseInt(disp.sonar.value)})
  }
  function listener(data) {
    if (override) return
    if (data.sonarsig) disp.sonar.value = 100 * data.sonarsig
  }
  function sendto(sender_) {
    sender = sender_
  }
  return {
    listener,
    sendto,
  }
}

export const Kinect = (output) => {
  const disp = h.div({class: 'flex widget'}).of(
    h.div({class: 'header'}).of('kinect'),
    ui.v(
      ui.h(
        'presence ',
        h.button('override').of('override'),
        h.input('presence', {type: 'range', min: 0, max: 1, step: 0.05, value: 0.5}),
      ),
    ),
  ).into(output).els

  let override = false
  disp.presence.disabled = true
  disp.override.addEventListener('click', () => {
    override = !override
    disp.override.classList.toggle('on')
    disp.presence.disabled = !override
    update()
  })
  disp.presence.addEventListener('change', update)

  let sender
  function update() {
    if (!override) {
      if (sender) sender({presence: null})
      return
    }
    if (sender) sender({presence: parseFloat(disp.presence.value)})
  }
  function listener(data) {
    if (override) return
    if (data.hasOwnProperty('presence')) disp.presence.value = data.presence
  }
  function sendto(sender_) {
    sender = sender_
  }
  return {
    listener,
    sendto,
  }
}

export const Debug = (output, { network, record_timestamps }) => {
  const disp = h.div({class: 'flex widget'}).of(
    h.div({class: 'header'}).of('debug'),
    h.button('download').of('download traces')
  ).into(output).els
  disp.download.addEventListener('click', network.download_timestamps)
  disp.download.style.display = record_timestamps ? 'inline-block' : 'none'
}

export const Recorder = (output) => {
  const disp = h.div({class: 'flex'}).of(
    h.div({class: 'flex widget'}).of(
      h.div({class: 'header'}).of('recorder'),
      h.div('cont').of(
        h.div('record', {class: 'record'}).of(
          h.input('input', {type: 'text'}),
          h.span('name', {class: 'name'}),
          h.button('start', {class: 'start'}).of('start'),
          h.button('stop', {class: 'stop'}).of('stop'),
        ),
        h.div('playback', {class: 'playback'}).of(
          h.div().of(
            h.select('sel').of(h.option({value: ''})),
            h.input('loop', {id: 'loop', type: 'checkbox'}),
            h.label({for: 'loop'}).of('loop'),
          ),
          h.div().of(
            h.div('bars', {class: 'bars'}),
            h.div('dt', {class: 'dt'}),
          ),
        ),
      ),
    ),
  ).into(output).els

  disp.input.addEventListener('change', e => {
    disp.name.textContent = e.target.value
  })
  disp.input.addEventListener('keyup', e => {
    if (e.keyCode === 13) {
      disp.start.dispatchEvent(new Event('click'))
    }
  })
  disp.start.addEventListener('click', () => {
    const record = disp.input.value
    if (!record) return
    sender({recorder: { record } })
    disp.sel.value = ''
    disp.record.classList.toggle('recording')
  })
  disp.stop.addEventListener('click', () => {
    sender({recorder: { record: null } })
    disp.record.classList.toggle('recording')
  })

  let recs, playback, bari
  fetch('/recordings').then(res => res.json()).then(recordings => {
    recs = recordings
    const names = Object.keys(recs)
    names.sort()
    names.reverse()
    names.forEach(name => {
      h.option({value: name}).of(name).into(disp.sel)
    })
  })
  disp.sel.addEventListener('change', e => {
    playback = e.target.value || null
    sender({recorder: { playback } })
    disp.bars.innerHTML = ''
    bari = 0
    if (!playback) return
    recs[playback].envelope.forEach(value => {
      const height = Math.max(2, Math.min(150, Math.floor(value**2 * 20)))
      h.span({style: `height:${height}px`}
      ).of(' ').into(disp.bars)
    })
  })
  disp.loop.addEventListener('change', e => {
    const loop = e.target.checked
    sender({recorder: { loop } })
  })
  disp.bars.addEventListener('click', e => {
    if (!playback) return
    const rect = disp.bars.getBoundingClientRect()
    const t = recs[playback].secs * ((e.pageX - rect.left) / rect.width)
    sender({recorder: { t } })
  })

  function secsmin(secs) {
    const min = Math.floor(secs / 60)
    secs = Math.floor(secs) % 60
    return `${min < 10 ? '0'+min : min}:${secs < 10 ? '0'+secs : secs}`
  }
  function update(fraction) {
    const uptobar =  fraction * recs[playback].envelope.length
    while (bari < uptobar) {
      disp.bars.children[bari++].classList.add('on')
    }
    while (bari - 1 >= uptobar) {
      disp.bars.children[--bari].classList.remove('on')
    }
    const secs = recs[playback].secs
    disp.dt.textContent = `${secsmin(fraction*secs)}/${secsmin(secs)}`
    const width = disp.playback.getBoundingClientRect().width
    const left = Math.floor(fraction * width)
  }
  function listener(signals) {
    if (!playback) return
    const t = signals.playback_t
    if ('undefined' === typeof(t)) return
    update(t / recs[playback].secs)
  }
  let sender
  function sendto(sender_) {
    sender = sender_
  }
  return {
    sendto,
    listener,
  }
}

export const Subsample = output => {
  const subsamples = [1, 2, 5, 10, 15, 20, 30]
  const disp = h.div({class: 'flex widget'}).of(
    h.div({class: 'header'}).of('subsample'),
    h.div({class: 'flex'}).of(
      h.button('full', {class: 'on'}).of('full on'),
      h.div('controls', {style: 'display: none'}).of(
        'recorder', h.select('recorder').of(subsamples.map(
          value => h.option({value}).of(`1/${value}`))),
        'animator', h.select('animator').of(subsamples.map(
          value => h.option({value}).of(`1/${value}`))),
      ),
    ),
  ).into(output).els
  disp.recorder.value = disp.animator.value = 10

  let full = true
  disp.full.addEventListener('click', () => {
    full = !full
    disp.full.classList.toggle('on')
    disp.controls.style.display = full ? 'none' : 'block'
    update()
  })
  function update() {
    sender({
      'recorder': {
        subsample: full ? 1 : parseInt(disp.recorder.value),
      },
      'animator': {
        subsample: full ? 1 : parseInt(disp.animator.value),
      },
    })
  }
  disp.recorder.addEventListener('change', update)
  disp.animator.addEventListener('change', update)

  let sender
  function sendto(sender_) {
    sender = sender_
  }
  return {
    sendto,
  }
}

export const Cmd = (output) => {
  const cont = h.div().into(output).el
  const notes = ['C2', 'D2', 'E2', 'F2']
  fetch('/setstates').then(res => res.json()).then(setstates => {
    let {colors, states} = setstates
    colors.unshift('')
    states.unshift('')
    const fcs = [0, 1, 2, 3]
    let disp = h.div({class: 'flex widget'}).of(
      h.div({class: 'header'}).of('cmd'),
      h.div({class: 'flex'}).of(
        'fc',
        h.select('fc').of(fcs.map(value =>
          h.option({value}).of(value))),
        'color',
        h.select('color').of(colors.map(value =>
          h.option({value}).of(value))),
        'state',
        h.select('state').of(states.map(value =>
          h.option({value}).of(value))),
        'midi',
        notes.map(note => h.button(note).of(note)),
      ),
    ).into(cont).els

    disp.fc.addEventListener('change', e => {
      sender({fc: e.target.value === '' ? null : parseInt(e.target.value)})
    })
    disp.color.addEventListener('change', e => {
      const color = e.target.value === '' ? null : e.target.value
      sender({setstate: { color }})
    })
    disp.state.addEventListener('change', e => {
      const state = e.target.value === '' ? null : e.target.value
      sender({setstate: { state }})
    })

    notes.forEach(note => {
      disp[note].addEventListener('mousedown', function() {
        this.classList.add('on')
        sender({midi: `0: ${note} on`})
      })
      disp[note].addEventListener('mouseup', function() {
        this.classList.remove('on')
        sender({midi: `0: ${note} off`})
      })
    })
  })

  let sender
  function sendto(sender_) {
    sender = sender_
  }
  return {
    sendto,
  }
}
