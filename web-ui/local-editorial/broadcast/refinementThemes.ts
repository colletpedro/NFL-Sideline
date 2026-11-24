import { broadcastThemes, neutralTheme } from './themes';
// Local surface assignments. Reference hex values/sources in themes.ts remain unchanged.
// These are design derivatives, not a claim of current official brand certification.
const plates: Record<string, { namePlate: string; nameInk: string; logoPlate: string; contextPlate: string; accent: string; logoShare: string; compactLogoShare: string }> = {
 BAL: { namePlate: '#241773', nameInk: '#F2F4F6', logoPlate: '#141319', contextPlate: '#38434B', accent: '#9E7C0C', logoShare: '22%', compactLogoShare: '29%' },
 DAL: { namePlate: '#B6BFC7', nameInk: '#002244', logoPlate: '#002244', contextPlate: '#002244', accent: '#869397', logoShare: '30%', compactLogoShare: '30%' },
 NE: { namePlate: '#002244', nameInk: '#F2F4F6', logoPlate: '#C60C30', contextPlate: '#38434B', accent: '#B0B7BC', logoShare: '33%', compactLogoShare: '32%' },
};
export function refinementTheme(team: string) {
 return { ...(broadcastThemes[team] ?? { ...neutralTheme, name: team }), ...(plates[team] ?? { namePlate: '#38434B', nameInk: '#F2F4F6', logoPlate: '#26323B', contextPlate: '#38434B', accent: '#A59376', logoShare: '25%', compactLogoShare: '29%' }) };
}
