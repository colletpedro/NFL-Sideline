import { expect, it } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';
import { TeamMedia } from './Media';
import { candidates, candidateFor } from './catalog';
import { MediaGallery } from './MediaGallery';
it('contains eight technically validated candidates with explicit rights and stable portrait associations',()=>{
  expect(candidates).toHaveLength(8);
  for(const a of candidates){expect(a.fileValidated).toBe(true);expect(a.reusePermission).toBe('UNVERIFIED');expect(a.sha256).toMatch(/^[a-f0-9]{64}$/);if(a.type==='portrait')expect(a.identifiers.gsis_id).toMatch(/^00-/);}
});
it('requires an explicit candidate preview and refuses a portrait for another team',()=>{
  const fallback=renderToStaticMarkup(<TeamMedia team="BAL" type="portrait"/>);
  expect(fallback).toContain('media-fallback');expect(fallback).not.toContain('Retrato de');
  const wrong=renderToStaticMarkup(<TeamMedia team="IND" type="portrait" allowCandidate asset={candidateFor('BAL','portrait')}/>);
  expect(wrong).toContain('media-fallback');expect(wrong).not.toContain('Derrick');
  const correct=renderToStaticMarkup(<TeamMedia team="BAL" type="portrait" allowCandidate/>);
  expect(correct).toContain('Derrick Henry');expect(correct).not.toContain('src="https://');expect(correct).toContain('width="3400"');
});
it('separates publication qualification and research candidates with consultable credit and limitations',()=>{
  const html=renderToStaticMarkup(<MemoryRouter><MediaGallery q={new URLSearchParams('week=3')}/></MemoryRouter>);
  expect(html).toContain('0 dos oito');expect(html).toContain('Candidatos de pesquisa local');expect(html).toContain('Fonte: Riddell');expect(html).toContain('Condições da fonte');expect(html).toContain('SHA-256');
});
