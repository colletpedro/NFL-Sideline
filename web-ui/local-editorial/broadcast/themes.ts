import balLogo from './assets/bal.png';
import dalLogo from './assets/dal.png';
import neLogo from './assets/ne.png';
export type TeamTheme = { city: string; name: string; primary: string; secondary: string; identity: string; identityLow: string; text: string; scene: string; logo?: string; logoScale: number; source: string };
// Identity references are independently checked in the sources below, not teamColors.ts.
// Gradient endpoints and scene tones are local design derivatives, not official colors.
export const broadcastThemes: Record<string, TeamTheme> = {
 BAL: { city: 'Baltimore', name: 'Ravens', primary: '#241773', secondary: '#9E7C0C', identity: '#241773', identityLow: '#191044', text: '#F2F4F6', scene: '#252133', logo: balLogo, logoScale: 1.6, source: 'https://usteamcolors.com/baltimore-ravens-team-colors/' },
 DAL: { city: 'Dallas', name: 'Cowboys', primary: '#002244', secondary: '#869397', identity: '#D0D6DC', identityLow: '#AEB9C3', text: '#002244', scene: '#202E3B', logo: dalLogo, logoScale: 1.08, source: 'https://coloropedia.com/dallas-cowboys-colors-team-logo/' },
 NE: { city: 'New England', name: 'Patriots', primary: '#002244', secondary: '#C60C30', identity: '#002244', identityLow: '#071726', text: '#F2F4F6', scene: '#252B35', logo: neLogo, logoScale: 1.65, source: 'https://www.brandcolorcode.com/new-england-patriots' },
};
export const neutralTheme: TeamTheme = { city: '', name: '', primary: '#3A4853', secondary: '#A59376', identity: '#3A4853', identityLow: '#26323B', text: '#F2F4F6', scene: '#252C30', logoScale: 1.6, source: 'Local neutral fallback, no team identity inferred' };
