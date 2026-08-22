import { useNavigate } from 'react-router-dom'
import { HowItWorks } from '../components/HowItWorks'

export function HowPage() {
  const navigate = useNavigate()
  return <HowItWorks onStart={() => navigate('/')} />
}
