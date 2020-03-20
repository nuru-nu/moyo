import { h, u, colors, Lines } from './smanmi/util.js'

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
          h.select('sel').of(h.option({value: ''})),
          h.input('loop', {id: 'loop', type: 'checkbox'}),
          h.label({for: 'loop'}).of('loop'),
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

  let recs
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
    const playback = e.target.value || null
    sender({recorder: { playback } })
  })
  disp.loop.addEventListener('change', e => {
    const loop = e.target.checked
    sender({recorder: { loop } })
  })

  function listener(signals) {
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

export const Cmd = (output) => {
  const cont = h.div().into(output).el
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
  })

  let sender
  function sendto(sender_) {
    sender = sender_
  }
  return {
    sendto,
  }
}
