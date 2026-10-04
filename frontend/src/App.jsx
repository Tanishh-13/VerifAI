import { useEffect, useRef, useState } from 'react'

import {
  AlertCircle,
  ArrowRight,
  Check,
  ExternalLink,
  FileImage,
  Globe,
  HelpCircle,
  Info,
  Link as LinkIcon,
  Newspaper,
  RefreshCw,
  Search,
  ShieldCheck,
  X,
  XCircle,
  CheckCircle2
} from 'lucide-react'


const API_URL = (
  import.meta.env.VITE_API_URL || 'http://localhost:8000'
).replace(/\/$/, '')


const steps = [
  'Reading the content…',
  'Finding the claim…',
  'Checking recent evidence…',
  'Comparing the claim with available reports…'
]


function normaliseResult(data) {
  const verification = data?.verification || {}
  const claim = data?.claim_analysis || {}

  return {
    ...data,

    verification: {
      conclusion:
        verification.conclusion ||
        verification.headline ||
        verification.reasoning ||
        'The claim could not be established from the available evidence.',

      explanation:
        verification.explanation ||
        verification.summary ||
        verification.reasoning ||
        '',

      evidence_analysis:
        verification.evidence_analysis || [],
    },

    claim_analysis: claim,

    evidence: Array.isArray(data?.evidence)
      ? data.evidence
      : [],
  }
}


/*
 * Convert any backend error into something readable.
 * This prevents errors like:
 *
 * [object Object]
 */
function getErrorMessage(data, fallback = 'Something went wrong.') {
  if (!data) return fallback

  if (typeof data === 'string') {
    return data
  }

  if (typeof data.detail === 'string') {
    return data.detail
  }

  if (Array.isArray(data.detail)) {
    return data.detail
      .map((item) => {
        if (typeof item === 'string') return item

        if (item?.msg) {
          return item.msg
        }

        return JSON.stringify(item)
      })
      .join(', ')
  }

  if (data.error && typeof data.error === 'string') {
    return data.error
  }

  if (data.message && typeof data.message === 'string') {
    return data.message
  }

  if (data.verification?.explanation) {
    return data.verification.explanation
  }

  try {
    return JSON.stringify(data)
  } catch {
    return fallback
  }
}


export default function App() {
  const [mode, setMode] = useState('image')

  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState('')

  const [url, setUrl] = useState('')

  const [loading, setLoading] = useState(false)
  const [step, setStep] = useState(0)

  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  const inputRef = useRef(null)
  const resultRef = useRef(null)


  useEffect(() => {
    if (!loading) return

    const timer = setInterval(() => {
      setStep((s) => Math.min(s + 1, steps.length - 1))
    }, 900)

    return () => clearInterval(timer)
  }, [loading])


  const chooseFile = (next) => {
    if (!next) return

    if (!next.type?.startsWith('image/')) {
      setError('Please choose a PNG, JPG, JPEG or WEBP image.')
      return
    }

    setError('')
    setFile(next)
    setResult(null)

    const reader = new FileReader()

    reader.onload = () => setPreview(reader.result)

    reader.readAsDataURL(next)
  }


  const clear = () => {
    setFile(null)
    setPreview('')
    setUrl('')
    setResult(null)
    setError('')

    if (inputRef.current) {
      inputRef.current.value = ''
    }
  }


  const verify = async () => {
    setError('')
    setResult(null)

    if (mode === 'image' && !file) {
      setError('Upload a screenshot first.')
      return
    }

    if (mode === 'url' && !url.trim()) {
      setError('Paste a link first.')
      return
    }

    setLoading(true)
    setStep(0)

    try {
      let response

      /*
       * SCREENSHOT VERIFICATION
       */
      if (mode === 'image') {
        const body = new FormData()

        body.append('file', file)

        response = await fetch(`${API_URL}/verify`, {
          method: 'POST',
          body
        })
      }

      /*
       * URL VERIFICATION
       *
       * IMPORTANT:
       * FastAPI currently defines:
       *
       * @app.post("/verify-url")
       * async def verify_url(url: str):
       *
       * Therefore "url" is a QUERY PARAMETER,
       * not a JSON body.
       */
      else {
        const encodedUrl = encodeURIComponent(url.trim())

        response = await fetch(
          `${API_URL}/verify-url?url=${encodedUrl}`,
          {
            method: 'POST'
          }
        )
      }


      /*
       * Read backend response
       */
      const text = await response.text()

      let data = null

      try {
        data = JSON.parse(text)
      } catch {
        throw new Error(
          text || `Backend returned ${response.status}`
        )
      }


      /*
       * Handle HTTP errors
       */
      if (!response.ok) {
        throw new Error(
          getErrorMessage(
            data,
            `Backend returned ${response.status}`
          )
        )
      }


      /*
       * Backend can return analysis_failed
       * while still returning HTTP 200.
       */
      if (data?.status === 'analysis_failed') {
        throw new Error(
          getErrorMessage(
            data,
            'VerifAI could not analyze this content.'
          )
        )
      }


      /*
       * Store successful result
       */
      setResult(normaliseResult(data))


      /*
       * Scroll to results
       */
      setTimeout(() => {
        resultRef.current?.scrollIntoView({
          behavior: 'smooth',
          block: 'start'
        })
      }, 80)

    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : getErrorMessage(
              e,
              'Could not connect to VerifAI backend.'
            )
      )

    } finally {
      setLoading(false)
    }
  }


  const conclusion =
    result?.verification?.conclusion || ''

  const explanation =
    result?.verification?.explanation || ''


  const isNegative =
    /contradict|false|not true|incorrect|debunk/i.test(
      conclusion
    )

  const isPositive =
    /support|true|accurate|confirmed/i.test(
      conclusion
    )


  return (
    <div className="min-h-screen bg-[#07090E] text-slate-100">

      {/* HEADER */}
      <header className="sticky top-0 z-30 border-b border-slate-800/80 bg-[#07090E]/90 backdrop-blur-xl">

        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">

          <div className="flex items-center gap-3">

            <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-indigo-500/30 bg-indigo-500/10 text-indigo-300">
              <ShieldCheck size={19} />
            </div>

            <div>
              <div className="font-semibold tracking-tight">
                VerifAI
              </div>

              <div className="hidden text-[11px] text-slate-500 sm:block">
                Check before you share.
              </div>
            </div>

          </div>


          <button
            onClick={() =>
              document
                .getElementById('how')
                ?.scrollIntoView({
                  behavior: 'smooth'
                })
            }
            className="text-sm text-slate-400 transition hover:text-white"
          >
            How it works
          </button>

        </div>

      </header>


      {/* MAIN */}
      <main className="mx-auto max-w-4xl px-4 pb-20 pt-12 sm:px-6">

        {/* HERO */}
        <section className="mb-10 text-center">

          <p className="mb-3 text-xs font-medium uppercase tracking-[0.2em] text-indigo-300">
            Viral claim checker
          </p>

          <h1 className="text-4xl font-bold tracking-tight text-white sm:text-5xl">
            Before you share it,{' '}
            <span className="text-indigo-300">
              verify it.
            </span>
          </h1>

          <p className="mx-auto mt-4 max-w-xl text-base leading-7 text-slate-400">
            Check screenshots and links against live news evidence and see exactly why VerifAI reached its conclusion.
          </p>

        </section>


        {/* INPUT CARD */}
        <section className="rounded-3xl border border-slate-800 bg-[#0F1420] p-4 shadow-2xl shadow-black/30 sm:p-6">

          {/* MODE SWITCH */}
          <div className="mb-5 flex gap-2 rounded-xl border border-slate-800 bg-[#07090E] p-1">

            <button
              onClick={() => {
                setMode('image')
                setError('')
              }}
              className={`flex flex-1 items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium ${
                mode === 'image'
                  ? 'bg-slate-800 text-white'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <FileImage size={16} />
              Screenshot
            </button>


            <button
              onClick={() => {
                setMode('url')
                setError('')
              }}
              className={`flex flex-1 items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium ${
                mode === 'url'
                  ? 'bg-slate-800 text-white'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <LinkIcon size={16} />
              Link
            </button>

          </div>


          {/* IMAGE MODE */}
          {mode === 'image' ? (

            <div
              onDragOver={(e) => e.preventDefault()}

              onDrop={(e) => {
                e.preventDefault()
                chooseFile(
                  e.dataTransfer.files?.[0]
                )
              }}

              onClick={() =>
                inputRef.current?.click()
              }

              className="cursor-pointer rounded-2xl border-2 border-dashed border-slate-800 bg-[#07090E]/60 p-10 text-center transition hover:border-indigo-500/50 hover:bg-[#07090E]"
            >

              <input
                ref={inputRef}
                type="file"
                accept="image/png,image/jpeg,image/webp"
                className="hidden"
                onChange={(e) =>
                  chooseFile(e.target.files?.[0])
                }
              />


              {preview ? (

                <div className="flex items-center justify-center gap-4">

                  <img
                    src={preview}
                    className="h-20 w-20 rounded-xl border border-slate-700 object-cover"
                    alt="Preview"
                  />

                  <div className="text-left">

                    <p className="max-w-[240px] truncate text-sm font-medium text-white">
                      {file?.name}
                    </p>

                    <p className="mt-1 text-xs text-slate-500">
                      Click to replace
                    </p>

                  </div>

                </div>

              ) : (

                <>
                  <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full border border-slate-800 bg-slate-900 text-indigo-300">
                    <FileImage size={21} />
                  </div>

                  <p className="text-sm font-medium text-slate-200">
                    Drop a screenshot here, or{' '}
                    <span className="text-indigo-300">
                      browse files
                    </span>
                  </p>

                  <p className="mt-1 text-xs text-slate-500">
                    PNG, JPG or WEBP
                  </p>
                </>

              )}

            </div>

          ) : (

            /* URL MODE */
            <div className="relative">

              <Globe
                className="absolute left-4 top-4 text-slate-500"
                size={18}
              />

              <input
                value={url}

                onChange={(e) => {
                  setUrl(e.target.value)
                  setError('')
                }}

                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !loading) {
                    verify()
                  }
                }}

                placeholder="Paste a news, Instagram, Facebook or X link…"

                className="w-full rounded-2xl border border-slate-800 bg-[#07090E] py-4 pl-11 pr-10 text-sm text-white outline-none transition placeholder:text-slate-600 focus:border-indigo-500/70"
              />


              {url && (

                <button
                  onClick={() => setUrl('')}
                  className="absolute right-4 top-4 text-slate-500 hover:text-white"
                >
                  <X size={17} />
                </button>

              )}

            </div>

          )}


          {/* ERROR */}
          {error && (

            <div className="mt-4 flex gap-3 rounded-xl border border-rose-900/60 bg-rose-950/30 p-4 text-sm text-rose-200">

              <AlertCircle
                className="shrink-0"
                size={18}
              />

              <span>{error}</span>

            </div>

          )}


          {/* VERIFY BUTTON */}
          <button
            disabled={loading}
            onClick={verify}
            className="mt-5 flex w-full items-center justify-center gap-2 rounded-2xl bg-indigo-600 py-3.5 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
          >

            {loading ? (

              <>
                <RefreshCw
                  size={17}
                  className="animate-spin"
                />
                Checking…
              </>

            ) : (

              <>
                Check this claim
                <ArrowRight size={17} />
              </>

            )}

          </button>

        </section>


        {/* LOADING */}
        {loading && (

          <section className="mt-7 rounded-2xl border border-slate-800 bg-[#0F1420] p-6 text-center">

            <Search
              className="mx-auto mb-3 animate-pulse text-indigo-300"
              size={25}
            />

            <p className="text-sm font-medium text-slate-200">
              {steps[step]}
            </p>

            <div className="mx-auto mt-4 h-1.5 max-w-xs overflow-hidden rounded-full bg-slate-900">

              <div
                className="h-full bg-indigo-500 transition-all duration-700"
                style={{
                  width: `${((step + 1) / steps.length) * 100}%`
                }}
              />

            </div>

          </section>

        )}


        {/* RESULTS */}
        {result && !loading && (

          <section
            ref={resultRef}
            className="mt-8 space-y-5"
          >

            {/* CONCLUSION */}
            <div
              className={`rounded-2xl border p-5 sm:p-6 ${
                isNegative
                  ? 'border-rose-600/40 bg-rose-950/25'
                  : isPositive
                    ? 'border-emerald-600/40 bg-emerald-950/20'
                    : 'border-amber-600/40 bg-amber-950/20'
              }`}
            >

              <div className="flex gap-3">

                <div className="pt-0.5">

                  {isNegative ? (
                    <XCircle className="text-rose-300" />
                  ) : isPositive ? (
                    <CheckCircle2 className="text-emerald-300" />
                  ) : (
                    <HelpCircle className="text-amber-300" />
                  )}

                </div>


                <div>

                  <p className="mb-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">
                    Conclusion
                  </p>

                  <h2 className="text-xl font-bold leading-snug text-white">
                    {conclusion}
                  </h2>

                </div>

              </div>

            </div>


            {/* EXPLANATION */}
            {explanation && (

              <div className="rounded-2xl border border-slate-800 bg-[#0F1420] p-5 sm:p-6">

                <h3 className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">

                  <Info
                    size={15}
                    className="text-indigo-300"
                  />

                  Why?

                </h3>

                <p className="text-sm leading-7 text-slate-300">
                  {explanation}
                </p>

              </div>

            )}


            {/* CLAIM */}
            {result.claim_analysis?.claim && (

              <div className="rounded-2xl border border-slate-800 bg-[#0F1420] p-5 sm:p-6">

                <h3 className="mb-3 text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
                  What was checked?
                </h3>

                <div className="rounded-xl border border-slate-800 bg-[#07090E] p-4 text-sm font-medium italic leading-6 text-slate-200">
                  “{result.claim_analysis.claim}”
                </div>

              </div>

            )}


            {/* EVIDENCE */}
            <div className="rounded-2xl border border-slate-800 bg-[#0F1420] p-5 sm:p-6">

              <div className="mb-4 flex items-center justify-between border-b border-slate-800 pb-3">

                <h3 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">

                  <Newspaper
                    size={15}
                    className="text-indigo-300"
                  />

                  Evidence

                </h3>

                <span className="text-xs text-slate-500">
                  {result.evidence.length} sources
                </span>

              </div>


              <div className="space-y-3">

                {result.evidence.map((item, i) => (

                  <article
                    key={i}
                    className="rounded-xl border border-slate-800 bg-[#07090E] p-4"
                  >

                    <div className="mb-2 flex flex-wrap items-center gap-2 text-xs text-slate-500">

                      <span className="font-semibold text-slate-300">
                        {item.source || 'News source'}
                      </span>

                      {item.published && (
                        <>
                          <span>•</span>
                          <span>{item.published}</span>
                        </>
                      )}

                    </div>


                    <h4 className="text-sm font-semibold leading-6 text-white">
                      {item.title}
                    </h4>


                    {item.url && (

                      <a
                        href={item.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-indigo-300 hover:text-indigo-200"
                      >
                        View source
                        <ExternalLink size={12} />
                      </a>

                    )}

                  </article>

                ))}

              </div>

            </div>


            {/* CHECK ANOTHER */}
            <button
              onClick={clear}
              className="mx-auto flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900 px-5 py-2.5 text-sm font-medium text-slate-300 hover:bg-slate-800"
            >

              <RefreshCw size={15} />

              Check another

            </button>

          </section>

        )}


        {/* HOW IT WORKS */}
        <section
          id="how"
          className="mt-20 border-t border-slate-800 pt-12"
        >

          <div className="mb-8 text-center">

            <h2 className="text-2xl font-bold text-white">
              How VerifAI works
            </h2>

            <p className="mt-2 text-sm text-slate-500">
              Simple on the surface, evidence-driven underneath.
            </p>

          </div>


          <div className="grid gap-4 md:grid-cols-3">

            {[
              [
                '01',
                'Extract',
                'Read the screenshot or linked content and identify the main factual claim.'
              ],
              [
                '02',
                'Find evidence',
                'Search current news reporting relevant to that exact claim.'
              ],
              [
                '03',
                'Compare',
                'Use the retrieved evidence to explain what can and cannot be established.'
              ]
            ].map(([n, t, d]) => (

              <div
                key={n}
                className="rounded-2xl border border-slate-800 bg-[#0F1420] p-5"
              >

                <div className="mb-3 font-mono text-2xl font-bold text-indigo-400/50">
                  {n}
                </div>

                <h3 className="font-semibold text-white">
                  {t}
                </h3>

                <p className="mt-2 text-sm leading-6 text-slate-500">
                  {d}
                </p>

              </div>

            ))}

          </div>

        </section>

      </main>


      {/* FOOTER */}
      <footer className="border-t border-slate-800 px-4 py-7 text-center text-xs text-slate-600">
        VerifAI · Check before you share.
      </footer>

    </div>
  )
}