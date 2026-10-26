import logoUrl from "../assets/logo.png";

export default function Logo({ height = 72 }: { height?: number }) {
  return <img src={logoUrl} alt="Dearly" height={height} style={{ height, width: "auto", display: "block" }} />;
}
