import { h } from './smanmi/util.js'

export const Recorder = (output, {network, defs}) => {
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
          h.div('playing .h').of(
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
    network.sender({recorder: { record } })
    disp.sel.value = ''
    disp.record.classList.toggle('recording')
  })
  disp.stop.addEventListener('click', () => {
    network.sender({recorder: { record: null } })
    disp.record.classList.toggle('recording')
  })

  let recs=defs.recordings, playback, bari
  const names = Object.keys(recs)
  names.sort()
  names.reverse()
  names.forEach(name => {
    h.option({value: name}).of(name).into(disp.sel)
  })
  disp.sel.addEventListener('change', e => {
    playback = e.target.value || null
    disp.playing.classList[playback ? 'remove' : 'add']('h')
    network.sender({recorder: { playback } })
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
    network.sender({recorder: { loop } })
  })
  disp.bars.addEventListener('click', e => {
    if (!playback) return
    const rect = disp.bars.getBoundingClientRect()
    const t = recs[playback].secs * ((e.pageX - rect.left) / rect.width)
    network.sender({recorder: { t } })
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
  network.listenJson('signals', function(signals) {
    if (!playback) return
    const t = signals.playback_t
    if ('undefined' === typeof(t)) return
    update(t / recs[playback].secs)
  })
}
