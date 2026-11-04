/** Turn model citations such as [Chunk ID: 12] into links the renderer can intercept. */
export function linkCitations(answer: string) {
  return answer.replace(/\[((?:\s*Chunk ID:\s*\d+\s*[,;]?\s*)+)\]/gi, (_match, inner: string) => {
    const ids = [...inner.matchAll(/\d+/g)].map((match) => match[0])
    return ids.map((id) => `[${id}](#cite-${id})`).join(' ')
  })
}
