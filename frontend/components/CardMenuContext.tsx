"use client";

//shared "which card's report menu is open" state. Without this, every
//CardView kept its own local boolean, so opening a menu on one card had
//no way to close the menu on another card.

import {
  createContext,
  ReactNode,
  useCallback,
  useContext,
  useState,
} from "react";

type Ctx = { openId: string | null; setOpenId: (id: string | null) => void };

const CardMenuContext = createContext<Ctx | null>(null);

export function CardMenuProvider({ children }: { children: ReactNode }) {
  const [openId, setOpenId] = useState<string | null>(null);
  return (
    <CardMenuContext.Provider value={{ openId, setOpenId }}>
      {children}
    </CardMenuContext.Provider>
  );
}

/** [isOpen, toggle] for one card's report menu. Opening one closes any other. */
export function useCardMenu(id: string): [boolean, () => void] {
  const ctx = useContext(CardMenuContext);
  if (!ctx)
    throw new Error("useCardMenu must be used inside <CardMenuProvider>");
  const isOpen = ctx.openId === id;
  const toggle = useCallback(
    () => ctx.setOpenId(isOpen ? null : id),
    [ctx, isOpen, id],
  );
  return [isOpen, toggle];
}
