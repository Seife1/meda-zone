import React, { createContext, useContext, useState, useEffect } from 'react'
import { useQuery } from 'react-query'
import { fieldsApi, Field } from '../api/fields'
import { useAuth } from '../hooks/useAuth'

interface FieldContextValue {
  fieldId: string | null
  setFieldId: (id: string) => void
  fields: Field[]
  currentField: Field | null
  isLoading: boolean
}

const FieldContext = createContext<FieldContextValue>({
  fieldId: null, setFieldId: () => {}, fields: [], currentField: null, isLoading: false,
})

export function FieldProvider({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, role } = useAuth()
  const [fieldId, setFieldId] = useState<string | null>(null)

  const { data: fields = [], isLoading } = useQuery(
    'myFields',
    () => fieldsApi.list().then((r) => r.data),
    { enabled: isAuthenticated, staleTime: 60_000 }
  )

  useEffect(() => {
    if (!fields.length) return
    const saved = localStorage.getItem('selected_field_id')
    if (saved && fields.find((f) => f.id === saved)) {
      setFieldId(saved)
      return
    }
    setFieldId(fields[0].id)
  }, [fields])

  const handleSet = (id: string) => {
    setFieldId(id)
    localStorage.setItem('selected_field_id', id)
  }

  const currentField = fields.find((f) => f.id === fieldId) ?? null

  return (
    <FieldContext.Provider value={{ fieldId, setFieldId: handleSet, fields, currentField, isLoading }}>
      {children}
    </FieldContext.Provider>
  )
}

export const useField = () => useContext(FieldContext)
